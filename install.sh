#!/bin/sh

echo "##S#W#I#R#L##1#.#5##############################################################"
echo ""

echo "Downloading spacy en_core_web_lg..."
python -m spacy download en_core_web_lg

echo "Downloading NLTK modules..."
python -m nltk.downloader stopwords
python -m nltk.downloader punkt

echo "If no errors occured, run python swirl.py setup"
