#!/bin/sh

PROG=$(basename $0)

lang_model_name=${SW_INSTALL_SPC_MODEL_NAME:-"en_core_web_lg"}
lang_model_name_dash=$(echo "$lang_model_name" | tr '_' '-')

if [ -f ".env" ]; then
    echo "$PROG Install: .env found"
else
    echo "$PROG Copying: .env.dist -> .env"
    cp .env.dist .env
fi

if [ -f "db.sqlite3" ]; then
    echo "$PROG Install: db.sqlite3 found"
else
    echo "$PROG Copying: db.sqlite3.dist -> db.sqlite3"
    cp db.sqlite3.dist db.sqlite3
fi

python swirl/banner.py
echo ""

echo "$PROG Installing dependencies:"
pip install --upgrade --no-cache-dir -r requirements.txt

echo "$PROG Checking for ${lang_model_name_dash}"
found_model=$(pip list 2>/dev/null | grep ${lang_model_name_dash} | awk '{print $1}')
if [ "x$found_model" = "x$lang_model_name_dash" ]; then
    echo "$PROG Found $lang_model_name , checking freshness...."
    # Check the version of the model and the software version of the spacy. If
    # the software version is not in the range of the model software version,then
    # down load the latest model.
    model_sw_version=$(python -m spacy info ${lang_model_name} | grep '^spacy_version' | awk '{print $2}')
    spacy_sw_version=$(pip show spacy | grep '^Version' | awk '{print $2}')
    min_version=$(echo $model_sw_version | awk -F '[<,>,=]' '{print $3}')
    max_version=$(echo $model_sw_version | awk -F '[<,>]' '{print $4}')
    echo $PROG : model_sw_version:$model_sw_version spacy_sw_version:$spacy_sw_version min_version:$min_version max_version:$max_version

    is_in_range=$(awk -v ver="$spacy_sw_version" -v min="$min_version" -v max="$max_version" 'BEGIN {
    split(ver, arrVer, ".");
    split(min, arrMin, ".");
    split(max, arrMax, ".");
    # Compare major versions
    # model_sw_version:>=3.5.0,<3.6.0 spacy_sw_version:3.6.1 min_version:3.5.0 max_version:3.6.0
    if (int(arrVer[1]) < int(arrMin[1]) || int(arrVer[1]) > int(arrMax[1])) {
	print "false_M";
	exit;
    }
    # If major version is equal to min major version, but minor version is out of range
    if (int(arrVer[1]) == int(arrMin[1]) && int(arrVer[2]) < int(arrMin[2])) {
	print "false_Ni";
	exit;
    }
    # If minor version is equal to min minor version, but patch version is out of range
    if (int(arrVer[2]) == int(arrMin[2]) && int(arrVer[3]) < int(arrMin[3])) {
	print "false_Pi";
	exit;
    }
    # If major version is equal to max major version, but minor version is out of range
    if (int(arrVer[1]) == int(arrMax[1]) && int(arrVer[2]) > int(arrMax[2])) {
	print "false_Nx";
	exit;
    }
    # If minor version is equal to max minor version, but patch version is out of range
    if (int(arrVer[2]) == int(arrMax[2]) && int(arrVer[3]) > int(arrMax[3])) {
	print "false_Px";
	exit;
    }

    # If everything is okay
    print "true";
}')
    if [ "$is_in_range" != "true" ]; then
	do_download=0
    else
	do_download=1
    fi

    ## Also check if pip thinks the model
    pip list -o 2>/dev/null | grep ${lang_model_name}
    pip_out_of_sync=$?
    if [ $pip_out_of_sync -eq 0 ]; then
	do_download=0
    fi

    echo $PROG : is_in_range:$is_in_range pip_out_of_sync:$pip_out_of_sync do_download:$do_download
    
    if [ $do_download -eq 0 ]; then
        echo "$PROG ${lang_model_name} is outdated. Downloading spacy ${lang_model_name}..."
        python -m spacy download en_core_web_lg
    else
        echo "$PROG ${lang_model_name} is up to date, skipping download"
    fi
else
    echo "$PROG Downloading spacy ${lang_model_name}..."
    python -m spacy download en_core_web_lg
fi

echo "$PROG Downloading NLTK modules..."
./download-nltk-resources.sh

echo "$PROG If no errors occurred, run python swirl.py setup"
