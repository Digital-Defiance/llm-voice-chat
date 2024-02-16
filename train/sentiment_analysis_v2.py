import torch
from torch import nn
from pydantic_settings import BaseSettings
from typing import  Optional, Dict, Any
from core.mixins import MyBaseSettingsMixin
from core.logger import get_logger
from core.constants import DEVICE
from model import ModelFactory, SentimentAnalysisModel
import gc
import numpy as np

logger = get_logger(__name__)


class TrainSettings(BaseSettings, MyBaseSettingsMixin):
    number_of_epochs: int = 100
    gpu_batch_size: int = 1024
    accumulation_steps: int = 1
    number_of_slices: int = 2
    l1_regularization: float = 0
    l2_regularization: float = 0
    beta_1: float = 0.9
    beta_2: float = 0.98
    epsilon: float = 1e-9
    warmup_steps: int = 4000
    lr_schedule_scaling: float = 1
    torch_seed: int = 1

    eval_interval: int = 1000
    model_save_interval: int = -1


    class Config:
        env_prefix = "TRAIN_"

class MLFlowSettings(BaseSettings, MyBaseSettingsMixin):
    run_id: Optional[str] = None
    experiment_id: int = 1
    run_name: Optional[str] = None
    nested: bool = False
    tags: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    log_system_metrics: Optional[bool] = True

    class Config:
        env_prefix = "MLFLOW_"

def cleanup_memory():
    logger.info(f"Cleaning up memory...")
    gc.collect()
    logger.info(f"Called garbage collector.")
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        logger.info(f"Emptied gpu cache.")



class Adam(torch.optim.Adam):
    def set_lr(self, lr: float) -> None:
        for param_group in self.param_groups:
            param_group['lr'] = lr

def load_data():
    train = np.load("data/asa/train.npz")
    rating, text = train["rating"], train["text"]
    rating = torch.tensor(rating.astype(np.int64))
    text = torch.tensor(text.astype(np.int32))
    return rating - 1, text

loss_function = nn.CrossEntropyLoss()

def yield_batches(rating: torch.Tensor, text: torch.Tensor, gpu_batch_size: int):
    cleanup_memory()
    random_idx = np.random.permutation(len(rating))
    rating = rating[random_idx]
    text = text[random_idx]
    del random_idx
    for start in range(0, len(rating), gpu_batch_size):
        end = start + gpu_batch_size
        rating_batch_b = rating[start:end].to(DEVICE)
        text_batch_bw = text[start:end].to(DEVICE)
        yield rating_batch_b, text_batch_bw

def train_step(
    model: nn.Module,
    rating_batch_b: torch.Tensor,
    text_batch_bw: torch.Tensor,
    optimizer: torch.optim.Optimizer
):
    model.train()
    pred_logits_b5 = model(text_batch_bw.int())
    loss_train = loss_function(pred_logits_b5, rating_batch_b)
    loss_train.backward()
    optimizer.step()
    optimizer.zero_grad()
    return model, loss_train.item()
 

def training_loop(
    train_settings: TrainSettings,
    model: nn.Module,
    rating: torch.Tensor,
    text: torch.Tensor,
    get_lr: callable,
):

    optimizer = Adam(model.parameters(), betas=(train_settings.beta_1, train_settings.beta_2), eps=train_settings.epsilon)
    metrics = { }
    step: int = 1

    for epoch in range(1, train_settings.number_of_epochs + 1):
        metrics["epoch"] = epoch
        logger.info(f"Epoch {epoch}")
        for rating_batch_b, text_batch_bw in yield_batches(rating, text, train_settings.gpu_batch_size):
            metrics["lr"] = get_lr(step)
            optimizer.set_lr(metrics["lr"])
            model, loss_train = train_step(model, rating_batch_b, text_batch_bw, optimizer)
            metrics["loss/train"] = loss_train
            yield model, metrics, step
            step += 1

def eval_model(model: nn.Module, rating: torch.Tensor, text: torch.Tensor):
    model.eval()
    with torch.no_grad():
        pred_logits_b5 = model(text.int())
        loss_eval = loss_function(pred_logits_b5, rating)

        # apply softmax to get probabilities
        pred_probs_b5 = torch.softmax(pred_logits_b5, dim=1)
        pred_rating_b = torch.argmax(pred_probs_b5, dim=1)

        # metric: confusion matrix
        confusion_matrix = torch.zeros(5, 5)
        for t, p in zip(rating.view(-1), pred_rating_b.view(-1)):
            confusion_matrix[t.long(), p.long()] += 1
        confusion_matrix = confusion_matrix / confusion_matrix.sum(1, keepdim=True)

    return model, loss_eval.item(), confusion_matrix.tolist()



if __name__ == "__main__":
    from mlflow import log_metrics, start_run, log_param, log_artifact, log_metrics
    import mlflow

    train_settings = TrainSettings()
    model_factory =  ModelFactory()
    mlflow_settings = MLFlowSettings()

    torch.manual_seed(train_settings.torch_seed)
    torch.autograd.set_detect_anomaly(True)

    logger.info(f"Using device {DEVICE}")
    logger.info(f"Using torch version {torch.__version__}")
    logger.info(f"Using mlflow version {mlflow.__version__}")

    def get_lr(step: int) -> float:
        lr = min(step ** -0.5, step * train_settings.warmup_steps ** -1.5)
        lr = lr * model_factory.coordinates ** -0.5
        lr = min(lr, 1e-3)
        return lr * train_settings.lr_schedule_scaling

    rating, text = load_data()
    text = text[:, :model_factory.words]

    model = SentimentAnalysisModel(model_factory).to(DEVICE)
    logger.info(f"Created model and moved it to {DEVICE}")

    n_parameters = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"Model has {n_parameters} parameters")

    with start_run(**mlflow_settings.model_dump()) as run:
        logger.info("Connected to MLFlow and started run.")
        model_factory.save_to_mlflow()
        train_settings.save_to_mlflow()
        log_param("number_of_parameters", n_parameters)
        logger.info("Saved training info and hyperparameters to MLFLow")

        for model, metrics, step in training_loop(train_settings, model, rating, text, get_lr):
            log_metrics(metrics, step=step)
            if step % train_settings.eval_interval == 0:
                continue
                model, loss_eval, confusion_matrix = eval_model(model, rating, text)
                log_metrics({"loss/eval": loss_eval}, step=step)
                log_metrics({"confusion_matrix": confusion_matrix}, step=step)
                logger.info(f"Logged eval metrics for step {step}")

            if train_settings.model_save_interval > 0 and step % train_settings.model_save_interval == 0:
                torch.save(model.state_dict(), f"model_{step}.pt")
                log_artifact(f"model_{step}.pt")
                logger.info(f"Saved model for step {step}")
        


            
