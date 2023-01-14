@echo off

if exist .env (
    echo "Install: .env found"
) else (
    echo "Copying: .env.dist -> .env"
    copy .env.dist .env
)

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
