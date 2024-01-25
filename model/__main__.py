
import torch.nn as nn
import tiktoken
from pydantic_settings import BaseSettings

from core.constants import DEVICE
from core.mixins import MyBaseSettingsMixin
from model.sequence_encoder import SequenceEncoder
from model.transformer_block import TransformerEncoderBlock, TransformerDecoderBlock, TransformerJunctionBlock
from typing import Literal, Optional
from pydantic import model_validator
from core.types import PositiveInt, TensorFloat, TensorInt

gpt2_encoder = tiktoken.get_encoding("gpt2")



class EncoderDecoder(nn.Module):
    def __init__(self, params: "ModelFactory", encoder: nn.Sequential):
        super(EncoderDecoder, self).__init__()

        self.sequence_encoder = encoder.pop(0)
        self.encoder = encoder

        self.junction_blocks = nn.ModuleList()
        for _ in range(params.number_of_blocks):
            self.junction_blocks.append(TransformerJunctionBlock(params))

        self.output_layer = nn.Sequential(
            nn.LayerNorm(params.coordinates),
            nn.Linear(params.coordinates, params.tokens, bias=params.bias)
        )

    
    def forward(self, auto_regress_sequence_bw: TensorInt, in_sequence_bw: TensorInt) -> TensorFloat:
        in_sequence_bwc = self.sequence_encoder(in_sequence_bw)
        auto_regress_sequence_bwc = self.sequence_encoder(auto_regress_sequence_bw)

        encoder_output_bwc = self.encoder(in_sequence_bwc)
        for junction_block in self.junction_blocks:
            auto_regress_sequence_bwc = junction_block(auto_regress_sequence_bwc, encoder_output_bwc)
        return self.output_layer(auto_regress_sequence_bwc)


        


class ModelFactory(BaseSettings, MyBaseSettingsMixin):
    coordinates: PositiveInt = 400
    tokens: PositiveInt = gpt2_encoder.max_token_value
    words: PositiveInt = 1000
    number_of_blocks: PositiveInt = 10
    number_of_heads: PositiveInt = 20
    bias: bool = False
    attention: Literal["metric", "scaled_dot_product"] = "scaled_dot_product"

    class Config:
        env_prefix = "MODEL_"

    @model_validator(mode='after')
    def validate(self) -> 'ModelFactory':
        assert self.coordinates % self.number_of_heads == 0, "Coordinates must be divisible by number of heads"
        return self

    def estimate_model_size(self) -> int:
        # calculate a rough estimate of the total number of parameters in the model
        n_sequence_encoder = self.coordinates * self.words + self.coordinates * self.tokens
        n_transformer_blocks = self.coordinates * self.coordinates * 4 * self.number_of_blocks
        n_layer_norm_c = self.coordinates * 2
        n_language_model_weights_tc = self.coordinates * self.tokens
        n_total = n_sequence_encoder + n_transformer_blocks + n_layer_norm_c + n_language_model_weights_tc
        return n_total
        # occupied_memory_gb = n_total * 4 / 1024 / 1024 / 1024
        # return self


    def create_model(self,  kind: Literal["encoder", "decoder", "encoder-decoder"] = "decoder") -> nn.Module:

        if kind == "decoder":
            return self._create_branch(kind)

        if kind == "encoder":
            return self._create_branch(kind)
        
        if kind == "encoder-decoder":
            return EncoderDecoder(self, self._create_branch("encoder"))
        

    def _create_branch(self, kind: Literal["encoder", "decoder"]) -> nn.Module:
        block = TransformerEncoderBlock if kind == "encoder" else TransformerDecoderBlock
        return nn.Sequential(
            SequenceEncoder(self),
            *[block(self) for _ in range(self.number_of_blocks)],
            nn.LayerNorm(self.coordinates),
            nn.Linear(self.coordinates, self.tokens, bias=self.bias),
        ).to(DEVICE)






    @classmethod
    def create_variant(cls, variant: str = "NanoGPT") -> nn.Module:
        """ DEPRECATED """

        assert variant in  ["NanoGPT", "NanoMTN"] , f"Unknown variant {variant}"

        if variant == "NanoGPT":
            return cls(
                words=100,
                coordinates=300,
                number_of_blocks=3,
                number_of_heads=3,
                bias = False,
                attention="scaled_dot_product"
            )

        if variant == "NanoMTN":
            return cls(
                words=100,
                coordinates=300,
                number_of_blocks=3,
                number_of_heads=3,
                bias = False,
                attention="metric"
            )
        



