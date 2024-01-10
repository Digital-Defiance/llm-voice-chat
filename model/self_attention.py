
import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor
from typing import Protocol
from abc import ABC, abstractmethod



# --- contracts --- #

class SelfAttentionParameters(Protocol):
    bias: bool
    coordinates: int
    words: int
    number_of_heads: int


class SelfAttention(ABC):
    MASK_ww: Tensor
    NUMBER_OF_HEADS: int
    COORDINATES: int
    K_DIMENSION: int


    def set_common_parameters(self: nn.Module, params: SelfAttentionParameters):
        self.COORDINATES = params.coordinates
        self.NUMBER_OF_HEADS = params.number_of_heads
        self.K_DIMENSION = self.COORDINATES // self.NUMBER_OF_HEADS

        self.register_buffer(
            "MASK_11ww",
            torch
              .tril(torch.ones(params.words, params.words))
              .view(1, 1, params.words, params.words)
        )

    @abstractmethod
    def __init__(self, params: SelfAttentionParameters):
        ...

    @abstractmethod
    def forward(self, in_sequence_bwc: Tensor) -> Tensor:
        ...

    @abstractmethod
    def get_metric(self) -> Tensor:
        ...




# --- implementations --- #


class MetricSelfAttention(nn.Module, SelfAttention):

    def __init__(self, params: SelfAttentionParameters):
        super(MetricSelfAttention, self).__init__()

        self.set_common_parameters(params)

        self.projection_1nck = nn.Parameter(
            torch.randn(
                1,
                self.NUMBER_OF_HEADS,
                self.K_DIMENSION,
                self.COORDINATES
            )
        )

        self.halves = nn.Parameter(
            torch.randn(
                self.NUMBER_OF_HEADS,
                self.K_DIMENSION*(self.K_DIMENSION + 1) // 2 - self.K_DIMENSION
            )
        )

        self.diagonals = nn.Parameter(torch.randn(self.NUMBER_OF_HEADS, self.K_DIMENSION))

        self.mixer_cc = nn.Linear(
            params.coordinates,
            params.coordinates,
            bias=params.bias
        )

        self.register_buffer(
            "INDICES",
            torch.triu_indices(row=self.K_DIMENSION, col=self.K_DIMENSION, offset=1)
        )


    def get_metric(self) -> Tensor:
        metric_tensors_nkk = torch.zeros(self.NUMBER_OF_HEADS, self.K_DIMENSION, self.K_DIMENSION)
        metric_tensors_nkk[:, self.INDICES[0], self.INDICES[1]] = self.halves
        return metric_tensors_nkk + metric_tensors_nkk.t() + torch.diag(self.diagonals_nk)


    def forward(self, in_sequence_bwc: Tensor) -> Tensor:
        batch, words, coordinates = in_sequence_bwc.size()
        metric_tensors_nkk = self.get_metric()

        in_sequence_b1wc = in_sequence_bwc.unsqueeze(1)
        all_projections_bnwk = in_sequence_b1wc @ self.projection_1nck

        all_dot_products_bnww = all_projections_bnwk @ metric_tensors_nkk @ all_projections_bnwk.transpose(-1, -2)
        all_scaled_dot_products_bnww = all_dot_products_bnww / math.sqrt(self.K_DIMENSION)
        all_scaled_dot_products_bnww = all_scaled_dot_products_bnww.masked_fill(self.MASK_11ww[:,:,:words,:words] == 0, float('-inf'))
        all_scaled_dot_products_bnww = F.softmax(all_scaled_dot_products_bnww, dim=-1)

        nudged_vectors_bnwk = all_dot_products_bnww @ all_projections_bnwk
        nudged_vectors_bwnk = nudged_vectors_bnwk.transpose(1, 2).contiguous()
        nudged_vectors_bwc = nudged_vectors_bwnk.view(batch, words, coordinates)

        out_sequence_bwc = self.mixer_cc(nudged_vectors_bwc)
        return out_sequence_bwc





class ScaledDotProductAttention(nn.Module, SelfAttention):
    attention_heads_dc: nn.Linear
    projection_cc: nn.Linear

    def __init__(self, params: SelfAttentionParameters):
        super(ScaledDotProductAttention, self).__init__()
        self.set_common_parameters(params)

        dimension = 3 * params.coordinates
    
        self.attention_heads_dc = nn.Linear(
            params.coordinates,
            dimension,
            bias=params.bias
        )

        self.projection_cc = nn.Linear(
            params.coordinates,
            params.coordinates,
            bias=params.bias
        )

    def forward(self, in_sequence_bwc: Tensor) -> Tensor:
 
        batch, words, coordinates = in_sequence_bwc.size()

        all_attention_vectors_bwd = self.attention_heads_dc(in_sequence_bwc)
        
        # split projections into three matrices
        #   - q_bwc contains all q vectors for the three heads
        #   - k_bwc contains all k vectors for the three heads
        #   - v_bwc contains all v vectors for the three heads
        q_bwc, k_bwc, v_bwc = all_attention_vectors_bwd.split(coordinates, dim=-1)
        
        
        # prepare for matrix multiplication
        k_dimension = coordinates // self.NUMBER_OF_HEADS
        q_b3wk = q_bwc.view(batch, words, self.NUMBER_OF_HEADS, k_dimension).transpose(1, 2)
        k_b3wk = k_bwc.view(batch, words, self.NUMBER_OF_HEADS, k_dimension).transpose(1, 2)
        v_b3wk = v_bwc.view(batch, words, self.NUMBER_OF_HEADS, k_dimension).transpose(1, 2)
      
        # perform matrix multiplication
        attention_scores_b3ww = q_b3wk @ k_b3wk.transpose(-1, -2)
        
        # prepare attention scores, scaling -> masking -> softmax
        attention_scores_b3ww = attention_scores_b3ww / math.sqrt(k_dimension)
        attention_scores_b3ww = attention_scores_b3ww.masked_fill(self.MASK_ww[:,:,:words,:words] == 0, float('-inf'))
        attention_scores_b3ww = F.softmax(attention_scores_b3ww, dim=-1)
        
        # produce the output sequence and shape it to the correct form
        out_sequence_b3wk = attention_scores_b3ww @ v_b3wk
        out_sequence_bw3k = out_sequence_b3wk.transpose(1, 2).contiguous()
        out_sequence_bwc = out_sequence_bw3k.view(batch, words, coordinates)
        
        # projection to mix the values 
        out_sequence_bwc = self.projection_cc(out_sequence_bwc)

        return out_sequence_bwc


    def get_metric(self) -> Tensor:
        raise NotImplementedError
        coordinates = self.COORDINATES
        WQ, WK, _ = self.attention_heads_dc.weight.transpose(-1, -2).split(coordinates , dim=-1)
        k_dimension = coordinates // self.NUMBER_OF_HEADS
        WQ = WQ.view(coordinates, self.NUMBER_OF_HEADS, k_dimension).transpose(0, 1)
        WK = WK.view(coordinates, self.NUMBER_OF_HEADS, k_dimension).transpose(0, 1)
        M = WQ @ WK.transpose(-1, -2)
        return M

