
from torch import Tensor
import torch.nn as nn
from model.sequence_encoder import SequenceEncoder
from model.transformer_block import TransformerBlock
from typing import Protocol
from model.l2_norm import L2Normalization

TensorInt = Tensor
TensorFloat = Tensor

class ModelParameters(Protocol):
    coordinates: int
    tokens: int
    words: int
    number_of_blocks: int
    number_of_heads: int
    bias: bool

class MetricTensorNetwork(nn.Module):

    sequence_encoder: SequenceEncoder
    transformer_blocks: nn.Sequential
    layer_norm_c: L2Normalization
    language_model_weights_tc: nn.Linear

    def __init__(self, params: ModelParameters):
        super(MetricTensorNetwork, self).__init__()

        self.sequence_encoder = SequenceEncoder(params)

        transformer_blocks = [TransformerBlock(params) for _ in range(params.number_of_blocks)]
        self.transformer_blocks = nn.Sequential(*transformer_blocks)

        self.layer_norm_c = L2Normalization(params)
        self.language_model_weights_tc = nn.Linear(params.coordinates, params.tokens, bias=params.bias)

    def forward(self, in_sequence_bw: TensorInt) -> TensorFloat:
        sequence_bwc = self.sequence_encoder(in_sequence_bw)
        sequence_bwc = self.transformer_blocks(sequence_bwc)
        sequence_bwc = self.layer_norm_c(sequence_bwc)
        logits_bwt = self.language_model_weights_tc(sequence_bwc)
        return logits_bwt

