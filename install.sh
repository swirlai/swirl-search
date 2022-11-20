#!/bin/sh

echo "##S#W#I#R#L##1#.#6##############################################################"
echo ""

echo "Installing dependencies:"
pip install -r requirements.txt

echo "Downloading spacy en_core_web_lg..."
python -m spacy download en_core_web_lg

echo "Downloading NLTK modules..."
python -m nltk.downloader stopwords
python -m nltk.downloader punkt

echo "If no errors occured, run python swirl.py setup"
