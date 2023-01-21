#!/bin/sh

if [ -f ".env" ]
then
echo "Install: .env found"
else
    echo "Copying: .env.dist -> .env"
    cp .env.dist .env
fi

if [ -f "db.sqlite3" ]
then
echo "Install: db.sqlite3 found"
else
    echo "Copying: db.sqlite3.dist -> db.sqlite3"
    cp db.sqlite3.dist db.sqlite3
fi

python swirl/banner.py
echo ""

echo "Installing dependencies:"
pip install -r requirements.txt

echo "Downloading spacy en_core_web_lg..."
python -m spacy download en_core_web_lg

echo "Downloading NLTK modules..."
python -m nltk.downloader stopwords
python -m nltk.downloader punkt

echo "If no errors occured, run python swirl.py setup"
