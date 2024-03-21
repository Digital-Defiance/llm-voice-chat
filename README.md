# LLM Voice Chat

Speak with a language model.

---

## Cuda Kernel


Let $P$ be a projection of a sequence $x$ of $c$ $d$-dimensional embeddings onto $n$ spaces of dimension $k$, expressed by

$$p^{nck} = P^{nk}_d  x^{cd}$$

At the heart of the proposed attention mechanism is the dot product of each embedding with each other embedding using $n$ learnable metric tensors $M$, given by

$$q^{ncc'} = M^{n}_{kk'} p^{nck} p^{nc'k'}$$

Noting that the metric tensor is symmetric, we can reduce the number of computations by grouping the terms strategically, that is, since $M_{kk'} = M_{k'k}$, then

$$q^{ncc'} = \delta_{kk'} M^n_{kk'} p^{nck} p^{nc'k'} + 2 \delta_{k>k'} M^n_{kk'} p^{nck} p^{nc'k'}$$

Let $F(k, k')$ be a pairing function that indexes an upper triangular matrix and $f$ and $g$ integer valued functions that retrieve the first and second argument of $F$, that is

$$  k = f(F(k, k')) $$

and

$$ k' = g(F(k, k')) $$

Such an arrangement is easily achieved computationally by storing two arrays to be used as a lookup table for $f$ and $g$. Finally, let $l=F(k, k')$, and 

$$ \bar M^n_{l} =  M^n_{f(l)g(l)} $$

we thus rewrite our expression as

$$q^{ncc'} = \delta_{f(l)g(l)} \bar M^n_{l} p^{ncf(l)} p^{nc'f(l)} + 2 \tilde \delta_{f(l)g(l)}   \bar M^n_l p^{ncf(l)} p^{nc'g(l)}$$

where $\tilde \delta_{f(l)g(l)} = 1 - \delta_{f(l)g(l)} $. At this point, our expression already fits quite well inside a cuda kernel, note how the $\delta$'s neatly define which expression needs to be calculated for a given value of $l$ and how easily that can be determined with an if-statement on $l$. However, a further computational saving is unlocked with the usage of a metric tensor. Since dot products are comutative, we thus have that $q^{ncc'} =q^{nc'c}$ and the procedure we just did for $kk'$ can be done for $cc'$. 

Let's use the same pairing function on the triangle matrix spanned by the range of $c$ and use the index $u$ to take the role of $l$ in this case. To avoid overuse of notation, the convention I'll use is that when $f$ and $g$ act on $l$, they'll recover $k$ and $k'$, but when they act on $u$, they'll recover $c$ and $c'$. 

To avoid repetition, I'll do the treatment for the following expression 

$$\rho^{ncc'l} = p^{ncf(l)} p^{nc'g(l)}$$

and perform symbol substitution where necessary in order to place it back on the expression we're working. Performing direct substitution we get

$$\rho^{nul} = p^{nf(u)f(l)} p^{ng(u)g(l)}$$

which we can similarly split into two expressions

$$\rho^{nul} = \delta_{f(u)g(u)} p^{nf(u)f(l)} p^{ng(u)g(l)} + 2  \tilde \delta_{f(u)g(u)}   p^{nf(u)f(l)} p^{ng(u)g(l)}$$

Note that further contraction is possible on the first term but $\delta$ cannot be removed otherwise $u$ spans the entire triangular matrix, so we get 

$$\rho^{nul} = \delta_{f(u)g(u)} p^{nf(u)f(l)} p^{nf(u)g(l)} + 2  \tilde \delta_{f(u)g(u)}   p^{nf(u)f(l)} p^{ng(u)g(l)}$$

Substituting this back, while attending to the relevant substitution on the first term of the original expression,


$$q^{nu} = \delta_{f(l)g(l)} \bar M^n_{l} \left [ \delta^{f(u)g(u)} p^{nf(u)f(l)} p^{nf(u)f(l)} + 2  \tilde \delta^{f(u)g(u)}   p^{nf(u)f(l)} p^{ng(u)f(l)} \right ]  + 2 \tilde \delta_{f(l)g(l)}   \bar M^n_l \left [ \delta^{f(u)g(u)} p^{nf(u)f(l)} p^{nf(u)g(l)} + 2  \tilde \delta^{f(u)g(u)}   p^{nf(u)f(l)} p^{ng(u)g(l)} \right ]$$

which we'll now group according to the $\delta$'s

$$q^{nu} =   \left [ \bar M^n_{l} p^{nf(u)f(l)} p^{nf(u)f(l)} \delta_{f(l)g(l)} \delta^{f(u)g(u)}  +   2 \bar M^n_{l}  p^{nf(u)f(l)} p^{ng(u)f(l)} \delta_{f(l)g(l)} \tilde \delta^{f(u)g(u)} \right ]  + \left [   2    \bar M^n_l p^{nf(u)f(l)} p^{nf(u)g(l)} \delta^{f(u)g(u)} \tilde \delta_{f(l)g(l)} + 4   \bar M^n_l   p^{nf(u)f(l)} p^{ng(u)g(l)} \tilde \delta^{f(u)g(u)} \tilde \delta_{f(l)g(l)} \right ]$$


----




## Experiments

Note: all workflows have been removed, pipelines are being moved to prefect

| Name and Status | Dataset | Usability | Workflow Badge |
|-----------------|---------|-----------|----------------|
| Sentiment Analysis Task (Completed with success) | [asa-v0.2.0](https://github.com/Digital-Defiance/llm-voice-chat/releases/tag/asa-v0.2.0) | Outdated | [![train-model: Sentiment Analysis Amazon Reviews @ EC2 Spot](https://github.com/Digital-Defiance/llm-voice-chat/actions/workflows/train-model-sentiment-analysis-task-asa.yml/badge.svg?branch=main)](https://github.com/Digital-Defiance/llm-voice-chat/actions/workflows/train-model-sentiment-analysis-task-asa.yml) |
| Sentiment Analysis Task (Completed without success, model overfits easily) | stanford dataset | Outdated | [![train-model: Sentiment Analysis @ EC2 Spot](https://github.com/Digital-Defiance/llm-voice-chat/actions/workflows/train-model-sentiment-analysis-task.yml/badge.svg)](https://github.com/Digital-Defiance/llm-voice-chat/actions/workflows/train-model-sentiment-analysis-task.yml) |
| GPT Shakespeare Textgen (Completed with success) | [sha-v0.1.0](https://github.com/Digital-Defiance/llm-voice-chat/releases/tag/sha-v0.1.0) | Outdated | [![GPT Array Sorter Experiment](https://github.com/Digital-Defiance/llm-voice-chat/actions/workflows/gpt_shakespear_experiment.yml/badge.svg)](https://github.com/Digital-Defiance/llm-voice-chat/actions/workflows/gpt_shakespear_experiment.yml) |
| GPT Array Sorter Experiment (Completed with success) | Generated | Outdated | [![GPT Array Sorter Experiment](https://github.com/Digital-Defiance/llm-voice-chat/actions/workflows/python-app.yml/badge.svg)](https://github.com/Digital-Defiance/llm-voice-chat/actions/workflows/python-app.yml) |




## Roadmap
https://github.com/orgs/Digital-Defiance/projects/11/views/1

### Phase 1

In this phase I am exploring a transformer variant and laying the groundwork for an ablation study similar to the one made on the MetaFormer (for vision). This phase is also primarily for me to build up my knowledge of NLP, data engineering, MLOps and large scale model training while hopefully getting some useful research done. 

- [x] implement and train a simple gpt that sorts tokens - [![GPT Array Sorter Experiment](https://github.com/Digital-Defiance/llm-voice-chat/actions/workflows/python-app.yml/badge.svg)](https://github.com/Digital-Defiance/llm-voice-chat/actions/workflows/python-app.yml)
- [x] use simpler implementation to contruct the MLOps infra
- [x] train a larger gpt on shakespeare - [![GPT Array Sorter Experiment](https://github.com/Digital-Defiance/llm-voice-chat/actions/workflows/gpt_shakespear_experiment.yml/badge.svg)](https://github.com/Digital-Defiance/llm-voice-chat/actions/workflows/gpt_shakespear_experiment.yml)
- [x] experiment with transformer modifications (i.e. mtn)
- [ ] perform systematic comparison between mtn and transformer
  - [ ] Sentiment Analysis 
    - [x] [![train-model: Sentiment Analysis @ EC2 Spot](https://github.com/Digital-Defiance/llm-voice-chat/actions/workflows/train-model-sentiment-analysis-task.yml/badge.svg)](https://github.com/Digital-Defiance/llm-voice-chat/actions/workflows/train-model-sentiment-analysis-task.yml)
    - [x]  [![train-model: Sentiment Analysis Amazon Reviews @ EC2 Spot](https://github.com/Digital-Defiance/llm-voice-chat/actions/workflows/train-model-sentiment-analysis-task-asa.yml/badge.svg?branch=main)](https://github.com/Digital-Defiance/llm-voice-chat/actions/workflows/train-model-sentiment-analysis-task-asa.yml)
  - [ ] topic classification
  - [ ] machine translation
  - [ ] summarization 
- [ ] write report on comparison between transformer and metric tensor network (might focus more on this depending on the results)


### Phase 2 

In this phase the plan is to deploy the models trained on phase 1, alongside with open source LLMs.

- [ ] write webapp (traefik - go + htmx + tmpl - fastapi + models)
- [ ] deploy webapp
- [ ] release first version

### Phase 3

In this phase, all the lessons from 1 and 2 will be used to to fine tune Lamma into multi-modility and finally, non-turn based voice chat. 

- [ ] fine tune gpt2
- [ ] fine tune lamma
- [ ] setup whisper




## possible dependencies

- https://github.com/mozilla/TTS

## some literature

- https://paperswithcode.com/method/strided-attention
- https://paperswithcode.com/method/fixed-factorized-attention
- https://paperswithcode.com/method/dot-product-attention
- https://paperswithcode.com/method/scaled

## datasets

- https://paperswithcode.com/dataset/cnn-daily-mail-1
- https://metatext.io/datasets/wikisummary

## The reasoning behind modifying transformers self attention 

NOTE: WIP

NOTE2: this is not the usual index notation, see next section for explanation

In the proposed self-attention mechanism, we consider a sequence input represented by a tensor $x_{bwc}$, where $b$ indexes the batch size, $w$ the sequence length, and $c$ the feature dimensions. The mechanism leverages a metric tensor to enhance the geometric understanding of the attention process proposed in 2017.

The first step involves a series of linear transformation of $x_{bwc}$ to $n$ lower-dimensional spaces. For each head $n$, this is achieved using a weight tensor $A_{ck}^{(n)}$ where $k = c / n$ represents the reduced dimensions for each head. The transformation is given by:

$$z_{bwk}^{(n)} = x_{bwc} A_{ck}^{(n)} $$


The heart of the mechanism lies in the metric tensor $G^{(n)} _ {kk}$, initialized as a product of a learnable, lower triangular tensor $P ^{(n)} _ {kk}$ and its transpose. This ensures that $G^{(n)} _ {kk}$ is symmetric and semi-positive definite:
$$G^{(n)}_{kk} = P ^{(n)} _ {kk} (P ^{(n)} _ {kk})^T$$
This introduces a geometric structure into the attention mechanism. The tensor $G^{(n)} _ {kk}$ allowes the network to construct custom dot products which can be calculated via the usual quadratic form,

$$ \textrm{dot}^{(n)}(z^{(n)} _ {bwk}, z^{(n)} _ {bwk}) = z^{(n)} _ {bwk} G^{(n)} _ {kk} ( z^{(n)} _ {bwk} ) ^T$$

We use this custom metric to replace the $W_qW_k^T$ shown in the original 2017 publication,

$$
S^{(n)}_ {bww} =
\text{softmax}_k\left( \frac{
\textrm{dot}^{(n)}(z^{(n)} _ {bwk}, z^{(n)} _ {bwk})
}{\sqrt{K}} \right)
$$

Here, $S^{(n)} _ {bww}$ represents the attention scores, quantifying the influence of each word in the sequence on every other word, with $w'$ indexing the sequence length. Once the attention scores are obtained, they are used to compute the output for each head. The output for head $n$, $O^{(n)}_{bwk}$, is a weighted sum of the transformed features:

$$O^{(n)}_ {bwk} = S^{(n)} _{bww} z^{(n)} _{bwk}$$

Finally, the outputs from all heads are concatenated and passed through another linear transformation $B_{ij}$ to yield the final output $Y_{bwi}$:

$$Y _{bwi} = B _{ij} \left[ O^{(1)} _ {bwj}, O^{(2)} _{bwj}, \ldots, O^{(N)} _{bwj} \right]$$

This mechanism, through the use of the metric tensor $G^{(n)}_{kk}$, provides a novel approach to compute attention, offering a geometric perspective to the understanding and processing of sequences in neural networks.



## Tensor Notation Guidelines

In our code, we use a specific notation to denote the shape of tensors. Here's how it works:

- A tensor's shape is indicated by appending a suffix to the variable name. Each letter in the suffix corresponds to a dimension in the tensor's shape. For example, a tensor with shape `(a, b, c)` would be named `some_tensor_abc`:

    ```python
    a, b, c = 10, 3, 5
    some_tensor_abc = torch.randn(a, b, c)
    ```

- If the dimensions of the tensor are not represented by single letters, we use their initials. For instance, a tensor with dimensions `batch_size` and `vocabolary_size` would be named `some_tensor_bv`:

    ```python
    batch_size, vocabolary_size = 32, 1024
    some_tensor_bv = torch.randn(batch_size, vocabolary_size)
    ```

- If a dimension has an explicit value, we include that value in the suffix. For example, `some_tensor_b2ac` indicates that the tensor has a second dimension (`dim=1`) with a size of 2. We only include explicit values in the suffix if they have more than one digit.

- We also extend this notation to functions. A function name like `some_function_tq` indicates that the function transforms dimension `q` into size `t`:

    ```python
    result_abct = some_function_tq(input_abcq)
    ```

This notation helps us keep track of tensor shapes throughout our code, making it easier to understand and debug.



# Preliminary Results

## Modified Self Attention, Metric Tensor Heads

![image](https://github.com/Digital-Defiance/llm-voice-chat/assets/63464503/5f17ae14-a627-4c0d-9a44-6b60e69f3774)

![image](https://github.com/Digital-Defiance/llm-voice-chat/assets/63464503/3bec2b7d-a47b-48bf-a7e0-b8a7c293a9e9)

![image](https://github.com/Digital-Defiance/llm-voice-chat/assets/63464503/b8026426-9d97-4379-8e08-f6c5a4722206)

## Loss Graph Comparison between Transformer and Metric Tensor Network

![2024-01-03-052123_571x464_scrot](https://github.com/Digital-Defiance/llm-voice-chat/assets/63464503/94534309-d07b-4ad2-9a87-9dcd23f012a2)

## Output Comparison

### Transformer:

```
The meaning of life is full of me:
if
I spy an age be content: the sea excuse that very
are to achieve for our prisoner to Rome's wife,
'Sirrah's see, command, let twenty pound
Strive might now; since is about me than,
Were then but the point of death: he were a
them where I'll wear what to wash you, for
And copy of the action; and gave me down himself
For why I should give for these fashion of them
Whether but relished to the hand:
Then speak, old and pray, no when the petition
With what, by our petition you bear this, after;
Not writ we held him. When like subjects put out,
That six years would reap the will we more
To follow us fly the throne of heaven, as sad
Which had no further. There, gentle Paulina,
The same no bodes with our valiant power,
And that's the herd, there be an his certain
Nor private gentlemen with you,--O, and your
Long may answer, from us, to fly seeing remorse,
The mutinous their eyes, who hath slain!
His senate-face, and my life sent,
The dangerous lenity where she starts;
And all with the sea or mistaken;
For him from whence can I do.

SOMERSET:
No310 of fear, here comes it.

ARCHBUSHY:
Ay, give? it not fall of this:
If thy mother shall be seen the world
Might gently before thyself in time.
MeDecline image and look'd, then, take him:
'Shall I we see thee thy tongue.

GREEN:
All Edward again. Give me to France, madam, I.
```


### metric tensor net

```
The meaning of life is soaking,'er's friend,
For I will in some man. It were to Richmond,
But by the general made up,
And when he walks, make him yea,
Thou shalt teach thee will to give himself?
Than Lewis he did I think of infirm'd too.

HASTINGS:
Under whom me so I swear to deliver me?

HASTINGS:

Ghost that I, a kingdom this amongst us.

BUCKINGHAM:
His lie such an Cates, he fears you.

KING EDWARD IV:
But raise this stands giftedave.

QUEEN MARGARET:
The rest be not your crown?

QUEEN ELIZABETH:
Is this once, that I enforce his sign of four
Which be uncle, till I let me to have done,
And not privy friend to a grief weep.
An, and my husband's wife hath done a want of mine.
My frost may follow to love.

Y ANNE:
The high forehead Margaret of Warwick mans your tongue and Derby,
To prove it of Buckingham shall way the streets.

QUEEN ELIZABETH:
Ay, by this device are butcher of Glouces;
Poor high love kill it will--

QUEEN ELIZABETH: may awake Boling;
And unblown, unto the cause
Or once to her repeal'd in private.
InsTER:
Come, no, the dying sovereign to my son and this land what
And were for Edward to thither to kill'd.
The knights and no conquest of them?
But do you be nor bestow' sovereign, nor debt:
Our children of Clarence, if 'tis trueborn blood.
Thus till then, my Edward is like our course of scful!
```

## preliminary conclusion

these results do not eliminate the modified network as a possible alternative to the transformer, but no significant advantages were found during training

according to gpt4, the output from the metric tensor net looks more coherent (I don't fully understand archaic english) but this is likely to be a coincidence

the metric tensor network was obtained from an ad hoc modification to the transformer, it does not yet make use of the reduced number of parameters to increase efficiency

----> the same results were obtained for the new architecture while making use of less parameters, could be a promising direction, more testing is needed. interpretability was not fully evaluated





