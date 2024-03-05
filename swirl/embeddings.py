'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

import logging
logger = logging.getLogger(__name__)

from pinecone import Pinecone
from transformers import AutoModel, AutoTokenizer
import torch

def get_embedding(text):
    model_name = "intfloat/e5-small-v2"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    # Tokenize and get embeddings
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    with torch.no_grad():
        outputs = model(**inputs)
    # Mean pooling
    embeddings = outputs.last_hidden_state.mean(dim=1)
    return embeddings[0].numpy()
