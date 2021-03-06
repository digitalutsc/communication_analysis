# Transcript Communication Analysis
A repository containing documentation and code for the analysis of structured communication such as AskChat transcripts and JIRA tickets. This is designed for our context, but the pattern can be followed to extend these analysis tools to other structured data formats. 

### Currently supports:
- [Ask a Librarian Service Logs](https://ask.scholarsportal.info/)
- [JIRA Service Logs](https://www.atlassian.com/software/jira)

### Features:
Given one or more .csv files containing relevant data:
- Identifies occurences of terms found in [text_terms_DS.txt](https://github.com/digitalutsc/communication_analysis/blob/main/text_terms_DS.txt)
- Identifies potential file extensions
- Identifies University of Toronto and University of Toronto Scarborough Course Codes
- Identifies proper nouns using [spacy](https://spacy.io/)
- Exports all occurrences ('hits') in a new csv with context and hit type, and removes columns that contain identifying information (e.g operator name, patron IP address)

### Requirements:
- Python 3
- [spacy v3.0+](https://spacy.io/usage)
- [spacy en_core_web_sm model](https://spacy.io/usage)
- A file with name 'text_terms_DS.txt' containing terms to query. Appropriate formatting can be found [here](https://github.com/digitalutsc/communication_analysis/blob/main/text_terms_DS.txt)
- If analyzing Ask Chat transcripts, a file with name 'names.csv' containing each name. Appropriate formatting can be found [here](https://github.com/digitalutsc/communication_analysis/blob/main/names.csv)

### Usage:
```bash
python3 script.py [mode] [file] [export_file]
```

```bash
python3 script.py ask_chat file1.csv export.csv
```

```bash
python3 script.py jira file1.csv file2.csv file3.csv export.csv
```

[mode] must be either 'ask_chat' or 'jira' depending on the input files. One or more input files may be added in between [mode] and [export_file]. Analysis data will be exported to a new file with name [export_file], assuming this file does not exist already.
