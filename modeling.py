# coding=utf-8
# Copyright 2018 The Google AI Language Team Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Common utility functions related to TensorFlow."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import copy
import json
import math
import six
import torch
import torch.nn as nn
from torch.nn import CrossEntropyLoss

def gelu(x):
    return x * 0.5 * (1.0 + torch.erf(x / math.sqrt(2.0)))
    # For information: OpenAI GPT gelu version is a bit different:
    # 0.5 * x * (1 + torch.tanh(math.sqrt(2 / math.pi) * (x + 0.044715 * torch.pow(x, 3))))


class BertConfig(object):
    """Configuration for `BertModel`."""

    def __init__(self,
                             vocab_size,
                             hidden_size=768,
                             num_hidden_layers=12,
                             num_attention_heads=12,
                             intermediate_size=3072,
                             hidden_act="gelu",
                             hidden_dropout_prob=0.1,
                             attention_probs_dropout_prob=0.1,
                             max_position_embeddings=512,
                             type_vocab_size=16,
                             initializer_range=0.02):
        """Constructs BertConfig.

        Args:
            vocab_size: Vocabulary size of `inputs_ids` in `BertModel`.
            hidden_size: Size of the encoder layers and the pooler layer.
            num_hidden_layers: Number of hidden layers in the Transformer encoder.
            num_attention_heads: Number of attention heads for each attention layer in
                the Transformer encoder.
            intermediate_size: The size of the "intermediate" (i.e., feed-forward)
                layer in the Transformer encoder.
            hidden_act: The non-linear activation function (function or string) in the
                encoder and pooler.
            hidden_dropout_prob: The dropout probabilitiy for all fully connected
                layers in the embeddings, encoder, and pooler.
            attention_probs_dropout_prob: The dropout ratio for the attention
                probabilities.
            max_position_embeddings: The maximum sequence length that this model might
                ever be used with. Typically set this to something large just in case
                (e.g., 512 or 1024 or 2048).
            type_vocab_size: The vocabulary size of the `token_type_ids` passed into
                `BertModel`.
            initializer_range: The sttdev of the truncated_normal_initializer for
                initializing all weight matrices.
        """
        self.vocab_size = vocab_size
        self.hidden_size = hidden_size
        self.num_hidden_layers = num_hidden_layers
        self.num_attention_heads = num_attention_heads
        self.hidden_act = hidden_act
        self.intermediate_size = intermediate_size
        self.hidden_dropout_prob = hidden_dropout_prob
        self.attention_probs_dropout_prob = attention_probs_dropout_prob
        self.max_position_embeddings = max_position_embeddings
        self.type_vocab_size = type_vocab_size
        self.initializer_range = initializer_range

    @classmethod
    def from_dict(cls, json_object):
        """Constructs a `BertConfig` from a Python dictionary of parameters."""
        config = BertConfig(vocab_size=None)
        for (key, value) in six.iteritems(json_object):
            config.__dict__[key] = value
        return config

    @classmethod
    def from_json_file(cls, json_file):
        """Constructs a `BertConfig` from a json file of parameters."""
        with open(json_file, "r") as reader:
            text = reader.read()
        return cls.from_dict(json.loads(text))

    def to_dict(self):
        """Serializes this instance to a Python dictionary."""
        output = copy.deepcopy(self.__dict__)
        return output

    def to_json_string(self):
        """Serializes this instance to a JSON string."""
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


class BERTLayerNorm(nn.Module):
    def __init__(self, config, variance_epsilon=1e-12):
        "Construct a layernorm module in the TF style (epsilon inside the square root)."
        super(BERTLayerNorm, self).__init__()
        self.gamma = nn.Parameter(torch.ones(config.hidden_size))
        self.beta = nn.Parameter(torch.zeros(config.hidden_size))
        self.variance_epsilon = variance_epsilon

    def forward(self, x):
        # TODO check it's identical to TF implementation in details (epsilon and axes)
        u = x.mean(-1, keepdim=True)
        s = (x - u).pow(2).mean(-1, keepdim=True)
        x = (x - u) / torch.sqrt(s + self.variance_epsilon)
        return self.gamma * x + self.beta
    #     tf.contrib.layers.layer_norm(
    #   inputs=input_tensor, begin_norm_axis=-1, begin_params_axis=-1, scope=name)

class BERTEmbeddings(nn.Module):
    def __init__(self, config):
        super(BERTEmbeddings, self).__init__()
        self.word_embeddings = nn.Embedding(config.vocab_size, config.hidden_size)

        # Position embeddings are (normally) a contiguous range so we could use a slice
        # Since the position embedding table is a learned variable, we create it
        # using a (long) sequence length `max_position_embeddings`. The actual
        # sequence length might be shorter than this, for faster training of
        # tasks that do not have long sequences.
        #
        # So `full_position_embeddings` is effectively an embedding table
        # for position [0, 1, 2, ..., max_position_embeddings-1], and the current
        # sequence has positions [0, 1, 2, ... seq_length-1], so we can just
        # perform a slice.
        self.position_embeddings = nn.Embedding(config.max_position_embeddings, config.hidden_size)

        # token_type_embeddings vocabulary is very small. TF used one-hot embeddings to speedup.
        self.token_type_embeddings = nn.Embedding(config.type_vocab_size, config.hidden_size)

        self.LayerNorm = BERTLayerNorm(config) # Not snake-cased to stick with TF model variable name
        self.dropout = nn.Dropout(config.hidden_dropout_prob)

    def forward(self, input_ids, token_type_ids=None):
        seq_length = input_ids.size(1)
        position_ids = torch.arange(seq_length, dtype=torch.long, device=input_ids.device)
        position_ids = position_ids.unsqueeze(0).expand_as(input_ids)
        if token_type_ids is None:
            token_type_ids = torch.zeros_like(input_ids)

        words_embeddings = self.word_embeddings(input_ids)
        position_embeddings = self.position_embeddings(position_ids)
        token_type_embeddings = self.token_type_embeddings(token_type_ids)

        embeddings = words_embeddings + position_embeddings + token_type_embeddings
        embeddings = self.LayerNorm(embeddings)
        embeddings = self.dropout(embeddings)
        return embeddings


class BERTSelfAttention(nn.Module):
    def __init__(self, config):
        super(BERTSelfAttention, self).__init__()
        if config.hidden_size % config.num_attention_heads != 0:
            raise ValueError(
                "The hidden size (%d) is not a multiple of the number of attention "
                "heads (%d)" % (config.hidden_size, config.num_attention_heads))
        self.num_attention_heads = config.num_attention_heads
        self.attention_head_size = int(config.hidden_size / config.num_attention_heads)
        self.all_head_size = self.num_attention_heads * self.attention_head_size

        self.query = nn.Linear(config.hidden_size, self.all_head_size)
        self.key = nn.Linear(config.hidden_size, self.all_head_size)
        self.value = nn.Linear(config.hidden_size, self.all_head_size)

        self.dropout = nn.Dropout(config.attention_probs_dropout_prob)

    def transpose_for_scores(self, x, is_key_tensor=False):
        new_x_shape = x.size()[:-1] + (self.num_attention_heads, self.attention_head_size)
        x = x.view(*new_x_shape)
        if is_key_tensor:
            return x.permute(0, 2, 3, 1)
        else:
            return x.permute(0, 2, 1, 3)

    def forward(self, hidden_states, attention_mask):
        # Scalar dimensions referenced here:
        #   B = batch size (number of sequences)
        #   F = `from_tensor` sequence length
        #   T = `to_tensor` sequence length
        #   N = `num_attention_heads`
        #   H = `size_per_head`
        mixed_query_layer = self.query(hidden_states)
        mixed_key_layer = self.key(hidden_states)
        mixed_value_layer = self.value(hidden_states)

        query_layer = self.transpose_for_scores(mixed_query_layer)
        key_layer = self.transpose_for_scores(mixed_key_layer) #, is_key_tensor=True)
        value_layer = self.transpose_for_scores(mixed_value_layer)

        # Take the dot product between "query" and "key" to get the raw
        # attention scores.
        # `attention_scores` = [B, N, F, T]
        attention_scores_no_norm = torch.matmul(query_layer, key_layer.transpose(-1, -2))
        attention_scores_no_mask = attention_scores_no_norm / math.sqrt(self.attention_head_size)

        # TODO clean up this (precompute)
        # MY PYTORCH: w = w * self.b + -1e9 * (1 - self.b)  # TF implem method: mask_attn_weights
        # `attention_mask` = [B, 1, F, T]
        # attention_mask = tf.expand_dims(attention_mask, axis=[1])
        # Since attention_mask is 1.0 for positions we want to attend and 0.0 for
        # masked positions, this operation will create a tensor which is 0.0 for
        # positions we want to attend and -10000.0 for masked positions.
        # adder = (1.0 - attention_mask) * -10000.0
        # Since we are adding it to the raw scores before the softmax, this is
        # effectively the same as removing these entirely.
        attention_scores = attention_scores_no_mask + attention_mask

        # Normalize the attention scores to probabilities.
        # `attention_probs` = [B, N, F, T]
        attention_probs_no_drop = nn.Softmax(dim=-1)(attention_scores)

        # This is actually dropping out entire tokens to attend to, which might
        # seem a bit unusual, but is taken from the original Transformer paper.
        attention_probs = self.dropout(attention_probs_no_drop)

        context_layer = torch.matmul(attention_probs, value_layer)
        context_layer = context_layer.permute(0, 2, 1, 3).contiguous()
        new_context_layer_shape = context_layer.size()[:-2] + (self.all_head_size,)
        context_layer = context_layer.view(*new_context_layer_shape)

        # aux_attention = attention_probs[0, 0, 0, :].view(1, 128, 1)
        # aux_attention = aux_attention.permute(0, 2, 1, 3).contiguous().view(1, 128, 768)
        # aux_attention = key_layer.permute(0, 2, 3, 1).contiguous().view(1, 128, 768)
        # aux_attention = key_layer.permute(0, 2, 1, 3).contiguous().view(1, 128, 768)

        return context_layer


class BERTSelfOutput(nn.Module):
    def __init__(self, config):
        super(BERTSelfOutput, self).__init__()
        self.dense = nn.Linear(config.hidden_size, config.hidden_size)
        self.LayerNorm = BERTLayerNorm(config)
        self.dropout = nn.Dropout(config.hidden_dropout_prob)

    def forward(self, hidden_states, input_tensor):
        hidden_states = self.dense(hidden_states)
        hidden_states = self.dropout(hidden_states)
        hidden_states = self.LayerNorm(hidden_states + input_tensor)
        return hidden_states


class BERTAttention(nn.Module):
    def __init__(self, config):
        super(BERTAttention, self).__init__()
        self.self = BERTSelfAttention(config)
        self.output = BERTSelfOutput(config)

    def forward(self, input_tensor, attention_mask):
        self_output = self.self(input_tensor, attention_mask)
        attention_output = self.output(self_output, input_tensor)
        return attention_output


class BERTIntermediate(nn.Module):
    def __init__(self, config):
        super(BERTIntermediate, self).__init__()
        self.dense = nn.Linear(config.hidden_size, config.intermediate_size)
        self.intermediate_act_fn = gelu

    def forward(self, hidden_states):
        hidden_states = self.dense(hidden_states)
        hidden_states = self.intermediate_act_fn(hidden_states)
        return hidden_states


class BERTOutput(nn.Module):
    def __init__(self, config):
        super(BERTOutput, self).__init__()
        self.dense = nn.Linear(config.intermediate_size, config.hidden_size)
        self.LayerNorm = BERTLayerNorm(config)
        self.dropout = nn.Dropout(config.hidden_dropout_prob)

    def forward(self, hidden_states, input_tensor):
        hidden_states = self.dense(hidden_states)
        hidden_states = self.dropout(hidden_states)
        hidden_states = self.LayerNorm(hidden_states + input_tensor)
        return hidden_states


class BERTLayer(nn.Module):
    def __init__(self, config):
        super(BERTLayer, self).__init__()
        self.attention = BERTAttention(config)
        self.intermediate = BERTIntermediate(config)
        self.output = BERTOutput(config)

    def forward(self, hidden_states, attention_mask):
        attention_output = self.attention(hidden_states, attention_mask)
        intermediate_output = self.intermediate(attention_output)
        layer_output = self.output(intermediate_output, attention_output)
        return layer_output


class BERTEncoder(nn.Module):
    def __init__(self, config):
        super(BERTEncoder, self).__init__()
        layer = BERTLayer(config)
        self.layer = nn.ModuleList([copy.deepcopy(layer) for _ in range(config.num_hidden_layers)])    

    def forward(self, hidden_states, attention_mask):
        """
        Args:
            hidden_states: float Tensor of shape [batch_size, seq_length, hidden_size]
        Return:
            float Tensor of shape [batch_size, seq_length, hidden_size]
        """
        all_encoder_layers = []
        for layer_module in self.layer:
            hidden_states = layer_module(hidden_states, attention_mask)
            all_encoder_layers.append(hidden_states)
        return all_encoder_layers


class BERTPooler(nn.Module):
    def __init__(self, config):
        super(BERTPooler, self).__init__()
        self.dense = nn.Linear(config.hidden_size, config.hidden_size)
        self.activation = nn.Tanh()

    def forward(self, hidden_states):
        """
        Args:
            hidden_states: float Tensor of shape [batch_size, seq_length, hidden_size]
        Return:
            float Tensor of shape [batch_size, hidden_size]
        """
        # We "pool" the model by simply taking the hidden state corresponding
        # to the first token. We assume that this has been pre-trained
        first_token_tensor = hidden_states[:, 0]
        pooled_output = self.dense(first_token_tensor)
        pooled_output = self.activation(pooled_output)
        return pooled_output


class BertModel(nn.Module):
    """BERT model ("Bidirectional Embedding Representations from a Transformer").

    Example usage:
    ```python
    # Already been converted into WordPiece token ids
    input_ids = torch.LongTensor([[31, 51, 99], [15, 5, 0]])
    input_mask = torch.LongTensor([[1, 1, 1], [1, 1, 0]])
    token_type_ids = torch.LongTensor([[0, 0, 1], [0, 2, 0]])

    config = modeling.BertConfig(vocab_size=32000, hidden_size=512,
        num_hidden_layers=8, num_attention_heads=6, intermediate_size=1024)

    model = modeling.BertModel(config=config)
    all_encoder_layers, pooled_output = model(input_ids, token_type_ids, input_mask)
    ```
    """
    def __init__(self, config: BertConfig):
        """Constructor for BertModel.

        Args:
            config: `BertConfig` instance.

        Raises:
            ValueError: The config is invalid or one of the input tensor shapes
                is invalid.
        """
        super(BertModel, self).__init__()
        self.embeddings = BERTEmbeddings(config)
        self.encoder = BERTEncoder(config)
        self.pooler = BERTPooler(config)

    def forward(self, input_ids, token_type_ids=None, attention_mask=None):
        # We create 3D attention mask from a 2D tensor mask.
        # Sizes are [batch_size, 1, 1, from_seq_length]
        # So we can broadcast to [batch_size, num_heads, to_seq_length, from_seq_length]
        # It's more simple than the triangular masking of causal attention, just need to
        # prepare the broadcast here
        if attention_mask is None:
            attention_mask = torch.ones_like(input_ids)
        if token_type_ids is None:
            token_type_ids = torch.zeros_like(input_ids)

        extended_attention_mask = attention_mask.unsqueeze(1).unsqueeze(2)
        extended_attention_mask = (1.0 - extended_attention_mask) * -10000.0

        embedding_output = self.embeddings(input_ids, token_type_ids)
        all_encoder_layers = self.encoder(embedding_output, extended_attention_mask)
        sequence_output = all_encoder_layers[-1]
        pooled_output = self.pooler(sequence_output)

        # TODO DEbugging
        # all_encoder_layers = [attention_mask, embeddings_sum, embedding_output] + all_encoder_layers
        return all_encoder_layers, pooled_output

class BertForSequenceClassification(nn.Module):
    """BERT model for classification.
    This module is composed of the BERT model with a linear layer on top of
    the pooled output.

    Example usage:
    ```python
    # Already been converted into WordPiece token ids
    input_ids = torch.LongTensor([[31, 51, 99], [15, 5, 0]])
    input_mask = torch.LongTensor([[1, 1, 1], [1, 1, 0]])
    token_type_ids = torch.LongTensor([[0, 0, 1], [0, 2, 0]])

    config = BertConfig(vocab_size=32000, hidden_size=512,
        num_hidden_layers=8, num_attention_heads=6, intermediate_size=1024)

    num_labels = 2

    model = BertForSequenceClassification(config, num_labels)
    logits = model(input_ids, token_type_ids, input_mask)
    ```
    """
    def __init__(self, config, num_labels):
        super(BertForSequenceClassification, self).__init__()
        self.bert = BertModel(config)
        self.dropout = nn.Dropout(config.hidden_dropout_prob)
        self.classifier = nn.Linear(config.hidden_size, num_labels)

        def init_weights(m):
            if isinstance(m, (nn.Linear, nn.Embedding)):
                print("Initializing {}".format(m))
                # Slight difference here with the TF version which uses truncated_normal
                # cf https://github.com/pytorch/pytorch/pull/5617
                m.weight.data.normal_(config.initializer_range)
        self.apply(init_weights)

    def forward(self, input_ids, token_type_ids, attention_mask, labels=None):
        _, pooled_output = self.bert(input_ids, token_type_ids, attention_mask)
        pooled_output = self.dropout(pooled_output)
        logits = self.classifier(pooled_output)

        if labels is not None:
            loss_fct = CrossEntropyLoss()
            loss = loss_fct(logits, labels)
            return loss, logits
        else:
            return logits

class BertForQuestionAnswering(nn.Module):
    """BERT model for Question Answering (span extraction).
    This module is composed of the BERT model with a linear layer on top of
    the sequence output that computes start_logits and end_logits

    Example usage:
    ```python
    # Already been converted into WordPiece token ids
    input_ids = torch.LongTensor([[31, 51, 99], [15, 5, 0]])
    input_mask = torch.LongTensor([[1, 1, 1], [1, 1, 0]])
    token_type_ids = torch.LongTensor([[0, 0, 1], [0, 2, 0]])

    config = BertConfig(vocab_size=32000, hidden_size=512,
        num_hidden_layers=8, num_attention_heads=6, intermediate_size=1024)

    model = BertForQuestionAnswering(config)
    start_logits, end_logits = model(input_ids, token_type_ids, input_mask)
    ```
    """
    def __init__(self, config):
        super(BertForQuestionAnswering, self).__init__()
        self.bert = BertModel(config)
        # TODO check if it's normal there is no dropout on SQuAD in the TF version
        # self.dropout = nn.Dropout(config.hidden_dropout_prob)
        self.qa_outputs = nn.Linear(config.hidden_size, 2)

        def init_weights(m):
            if isinstance(m, (nn.Linear, nn.Embedding)):
                print("Initializing {}".format(m))
                # Slight difference here with the TF version which uses truncated_normal for initialization
                # cf https://github.com/pytorch/pytorch/pull/5617
                m.weight.data.normal_(config.initializer_range)
            elif isinstance(m, BERTLayerNorm):
                m.beta.data.normal_(config.initializer_range)
                m.gamme.data.normal_(config.initializer_range)
            if isinstance(m, nn.Linear):
                m.bias.data.zero_()
        self.apply(init_weights)

    def forward(self, input_ids, token_type_ids, attention_mask, start_positions=None, end_positions=None):
        all_encoder_layers, _ = self.bert(input_ids, token_type_ids, attention_mask)
        sequence_output = all_encoder_layers[-1]
        logits = self.qa_outputs(sequence_output)
        start_logits, end_logits = logits.split(1, dim=-1)

        if start_positions is not None and end_positions is not None:
            #loss_fct = CrossEntropyLoss()
            #start_loss = loss_fct(start_logits, start_positions)
            #end_loss = loss_fct(end_logits, end_positions)
            batch_size, seq_length = input_ids.size()
            
            def compute_loss(logits, positions):
                max_position = positions.max().item()
                one_hot = torch.FloatTensor(batch_size, max(max_position, seq_length) +1).zero_()
                one_hot = one_hot.scatter_(1, positions.cpu(), 1) # Second argument need to be LongTensor and not cuda.LongTensor
                one_hot = one_hot[:, :seq_length].to(input_ids.device)
                log_probs = nn.functional.log_softmax(logits, dim = -1).view(batch_size, seq_length)
                loss = -torch.mean(torch.sum(one_hot*log_probs), dim = -1)
                return loss
            
            start_loss = compute_loss(start_logits, start_positions)
            end_loss = compute_loss(end_logits, end_positions)
            total_loss = (start_loss + end_loss) / 2
            return total_loss, (start_logits, end_logits)
        else:
            return start_logits, end_logits