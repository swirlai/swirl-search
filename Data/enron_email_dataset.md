# INDEXING THE ENRON DATA SET INTO ELASTIC SEARCH

## Procedure

* Download the enron email data set: [https://www.cs.cmu.edu/~enron/](https://www.cs.cmu.edu/~enron/)

* Gunzip and untar the download and place it in your SWIRL distribution root directory

* Create an index 'email' in elastic search:

```
PUT /email
```

* Run the email_load.py script in the SWIRL distribution:

```
python scripts/email_load.py enron-email.csv -e http://elastic-url -p password-for-elastic-user
```

* The script will report after every 100 messages are fed


