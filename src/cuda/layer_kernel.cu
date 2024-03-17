#include <cuda_runtime.h> 
#include <torch/extension.h>
#include <cuda.h>

#include <torch/torch.h>

using namespace torch::autograd;

#define CHECK_CUDA(x) TORCH_CHECK(x.device().is_cuda(), #x " must be a CUDA tensor")
#define CHECK_CONTIGUOUS(x) TORCH_CHECK(x.is_contiguous(), #x " must be contiguous")
#define CHECK_INPUT(x) CHECK_CUDA((*x)); CHECK_CONTIGUOUS((*x))

typedef torch::Tensor *TensorPTR;

template <typename scalar_t> 
__global__ void metric_attention_forwards_kernel(
        scalar_t *input_bcd,
        scalar_t *metric_1nkk,
        scalar_t *output_bcd
) {
    /// TODO metric_attention_forwards_kernel
    // int i = blockDim.x * blockIdx.x + threadIdx.x;
    // c[i] += a[i] + b[i];
}


template <typename scalar_t> 
__global__ void metric_attention_backwards_kernel(
        scalar_t *input_bcd,
        scalar_t *metric_1nkk,
        scalar_t *output_bcd
) {
    /// TODO metric_attention_backwards_kernel
    // int i = blockDim.x * blockIdx.x + threadIdx.x;
    // c[i] += a[i] + b[i];
}


class MetricTensorAttention : public Function<MetricTensorAttention> {
    public:
        static void
        forward(
            AutogradContext *ctx,
            TensorPTR input_bcd,
            TensorPTR metric_1nkk,
            TensorPTR output_bcd,
            int b, int c, int d, int n, int k
        ) {
            ctx->save_for_backward({input_bcd, metric_1nkk, output_bcd});

            AT_DISPATCH_FLOATING_TYPES(input_bcd->type(), "metric_attention_forwards_kernel", ([&] {
                metric_attention_backwards_kernel<scalar_t><<<2, 1>>>(
                    input_bcd->data<scalar_t>(),
                    metric_1nkk->data<scalar_t>(),
                    result->data<scalar_t>()
                );
            });
        }

        static tensor_list
        backward(
            AutogradContext *ctx,
            tensor_list grad_outputs
        ) {
            auto saved = ctx->get_saved_variables();
            // input_bcd, metric_1nkk, output_bcd
            auto input_bcd = saved[0];
            auto metric_1nkk = saved[1];
            auto output_bcd = saved[2];

            AT_DISPATCH_FLOATING_TYPES(input_bcd->type(), "metric_attention_backwards_kernel", ([&] {
                metric_attention_backwards_kernel<scalar_t><<<2, 1>>>(
                    input_bcd->data<scalar_t>(),
                    metric_1nkk->data<scalar_t>(),
                    result->data<scalar_t>()
                );
            });  
                  
            // auto grad_output = grad_outputs[0];
            // auto grad_input = grad_output.mm(weight);
            // auto grad_weight = grad_output.t().mm(input);

            return {}; // {grad_input, grad_weight};
  }
};


extern "C" {
    void f_metric_tensor_attention(TensorPTR input_bcd, TensorPTR output_bcd, TensorPTR metric_1nkk) {

        CHECK_INPUT(input_bcd);
        CHECK_INPUT(output_bcd);
        CHECK_INPUT(metric_1nkk);


        MetricTensorAttention::apply(
            input_bcd,
            output_bcd,
            metric_1nkk
        );
    }
}

