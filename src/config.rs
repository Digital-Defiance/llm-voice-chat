


use clap::Parser;
// use crate::metaformer::AttentionKind;

/// Train a MetaFormer model.
#[derive(Parser)]
#[command(version, about, long_about = None)]
pub struct Cli {
    #[arg(long)]
    pub encoding: String,
 
    /// The kind of attention to use.
    #[arg(long)]
    pub attention_kind: String,

    /// Dimension of the vector space that the network uses internally to represent tokens 
    #[arg(long)]
    pub dimension: i64,

    /// Number of transformer blocks
    #[arg(long)]
    pub depth: i64,

    /// Number of attention modules per transformer block
    #[arg(long)]
    pub heads: i64,

    /// Maximum number of tokens in the input sequence
    #[arg(long)]
    pub context_window: i64,

    /// Total number of tokens that the network recognizes in its input
    #[arg(long)]
    pub input_vocabolary: i64,

    /// Total number of tokens that the network recognizes in its outpput
    #[arg(long)]
    pub output_vocabolary: i64,

    /// Number of samples in a batch
    #[arg(long)]
    pub batch_size: i64,

    #[arg(long)]
    pub path_to_slice: String,

    #[arg(long)]
    pub learning_rate: f64,

    #[arg(long)]
    pub use_gpu: bool,

}



pub fn read_config() -> Cli {
    Cli::parse()
}

