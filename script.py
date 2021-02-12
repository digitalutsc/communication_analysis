import sys, csv, re, pandas, numpy, time
import spacy
from spacy import displacy
from collections import Counter
import math
import en_core_web_sm
nlp = spacy.load("en_core_web_sm")

#Text to analyze for query data and proper nouns must be in the column with index data_array_text_location
#JIRA csv files have varying locations for this column, so function get_jira_data_array_text_location() is used
data_array_text_location = 11

def convertcsv(filename):
    """
    Converts a csv file to a modifiable list & return it.
    Parameters:
        filename: The directory of the file. Must be in a .csv format
    Returns:
        A list with the 0th index containing the data of the csv in list object form and the 1st index containg a list object storing each column header.
    """
    data = pandas.read_csv(filename, engine="python")
    headers = data.columns.values.tolist()
    data = data.replace(numpy.nan, '', regex=True)
    data = data.to_numpy().tolist()
    return [data, headers]

def get_jira_data_array_text_location(headers):
    """
    For JIRA logs, sets global variable data_array_text_location to the column index with header "Description". All text in this column is to be analyzed by the script.
    Parameters:
        headers: A List containg the name of each column header.
    """
    global data_array_text_location
    data_array_text_location = headers.index("Description")

def patron_or_operator(chat_log, line_index):
    """
    Return whether a message was sent by an operator or a patron. Only applicable for ask chat logs.
    Parameters:
        chat_log: A chat log list
        line_index: The index of the message to be observed in the chat log.
    Returns:
        Return operator or patron if respective data was found in the message. If not, recursively call the function on the message prior to line_index
    """
    if MODE == "jira":
        return "N/A"
    if line_index < 0:
        return "Unable to find"
    if len(chat_log[data_array_text_location][line_index]) < 2:
        return patron_or_operator(chat_log, line_index - 1)
    text = chat_log[data_array_text_location][line_index][1].lower()
    ip = chat_log[1]
    profile = chat_log[3]
    queue = chat_log[4]
    operator = chat_log[8]
    if "operator" in text or profile in text or queue in text or operator in text:
        return "Operator"
    if ip in text or "patron" in text:
        return "Patron"
    return patron_or_operator(chat_log, line_index - 1)

def get_operator_institution(operator):
    """
    Return the institution of an operator.
    Parameters:
        operator: A string in format (operator_name)_(operator_institution).
    Returns:
        The institution of the operator
    For example, get_operator_institution('john_tor') -> 'tor'
    """
    return(operator[operator.find('_') + 1:])

def get_operator_data(operator, names):
    """
    Check if an operator is within a given list of names, and if so, return their role and sub-institution.
    Parameters:
        operator: A string in format (operator_name)_(operator_institution).
        names: A list of names, each in format [operator name, institutional suffix, real name, institution, role, campus].
    Returns:
        If a name is found in names, return a list with their role in the 0th index and sub-institution in the 1st index. Otherwise, both values are empty strings.
    """
    for name in names:
        if operator == name[0]:
            return [name[4], name[5]]
    return ["", ""]

def get_referrer_domain(link):
    """
    Return the domain of a referring link, given the link
    Precondition: Link contains 'http(s)://' and ends with a '/'
    Parameters:
        link: A string containing the link to remove any subdirectories
    Returns:
        A link with subdirectories stripped out
    For example, get_referrer_domain('https://outlook.office.com/mail/inbox/') -> 'https://outlook.office.com'
    """
    return(link[:link[link.find('://') + 3:].find('/') + link.find('://') + 3])

def split_sentences(data):
    """
    Splits a body of text by lines, then again by words
    Parameters:
        data: A csv in python list form
    Returns:
        data: A csv in python list form, where all text in column with index data_array_text_location split by lines and words
    """
    for i in range(len(data) - 1, -1, -1):
        data[i][data_array_text_location] = data[i][data_array_text_location].split('\n')
        for j in range(len(data[i][data_array_text_location]) - 1, -1, -1):
            data[i][data_array_text_location][j] = (data[i][data_array_text_location][j]).split() #Replace each line with a list of its words
            if data[i][data_array_text_location][j] == []: #Remove sentences with no words
                data[i][data_array_text_location].pop(j)
        #Add empty strings for return data
        for j in range(5):
            data[i].append([])
    return data

def line_to_string(line):
    """
    Converts a list of words to a string containing its contents as a line
    Parameters:
        line: A list where each object is a string containing a word
    Returns:
        output: A string containing each word in list seperated by a space
    """
    output = ""
    for word in line:
        for char in word:
            output = output + char
        output = output + " "
    return output

def append_hit_data(chat_log, hit_type, hit, hit_context, patron_or_operator, proper_noun_type=""):
    """
    Given a chat log and a hit, append all hit data to the chat log
    Parameters:
        chat_log: A chat log list
        hit_type: The string containing the type of hit
        hit: The string containing the text found
        hit_context: The string containing the message the hit was found in
        patron_or_operator: The string containing whether the message was sent by a patron or an operator
        proper_noun_type: If hit_type is equivalent to 'proper noun', the type of proper noun
    Returns:
        chat_log: A chat log list with all hit data appended
    """
    chat_log[len(chat_log) - 5].append(hit_type)
    chat_log[len(chat_log) - 4].append(hit)
    chat_log[len(chat_log) - 3].append(hit_context)
    chat_log[len(chat_log) - 2].append(patron_or_operator)
    chat_log[len(chat_log) - 1].append(proper_noun_type)
    return chat_log

def analyze_proper_nouns(data):
    """
    Find and analyze proper nouns using Spacy, given the whole data set
    Parameters:
        data: The list containing all data to analyze
    Returns:
        data: The list containing all data to analyze, with all hits appended to each chat log
    """
    all_logs = [] #A list of every chat log
    for i in range(len(data)): #Iterate over each chat log
        log = ""
        for j in range(len(data[i][data_array_text_location]) - 1, -1, -1): #Iterate over each line
            if len(data[i][data_array_text_location][j]) > 2:
                for k in range(len(data[i][data_array_text_location][j]) - 1, -1, -1): #Iterate over each word
                    if "http" in data[i][data_array_text_location][j][k].lower(): #Remove links
                        data[i][data_array_text_location][j].pop(k)
                patron_or_op = patron_or_operator(data[i], j)
                line_string = line_to_string(data[i][data_array_text_location][j][2:])
                #Mark whether sent by patron, operator, or neither
                if "system message" not in line_string.lower():
                    if patron_or_op == "Operator":
                        log = log + "chat_operator:" + line_string
                    elif patron_or_op == "Patron":
                        log = log + "chat_patron:" + line_string
                    else:
                        log = log + "chat_neither:" + line_string
        all_logs.append(log)
    docs = nlp.pipe(all_logs, disable=["tagger, parser"])
    i = 0
    for line in docs:
        for entity in line.ents:
            if entity.label_ != "CARDINAL" and entity.label_ != "ORDINAL" and entity.label_ != "QUANTITY" and entity.label_ != "MONEY" and entity.label_ != "PERCENT" and entity.label_ != "TIME" and entity.label_ != "DATE" and entity.text.lower() != "librarian" and "chat_operator" not in entity.text.lower() and "chat_patron" not in entity.text.lower() and "chat_neither" not in entity.text.lower():
                text = str(line[:entity.start])
                #Use earlier marking to track patron, operator, or neither
                oploc = text.rfind("chat_operator:")
                paloc = text.rfind("chat_patron:")
                neloc = text.rfind("chat_neither:")
                if oploc > paloc and oploc > neloc:
                    patron_or_op = "Operator"
                elif paloc > oploc and paloc > neloc:
                    patron_or_op = "Patron"
                elif neloc > oploc and neloc > paloc:
                    patron_or_op = "Unable to find"
                else:
                    patron_or_op = "Error"
                #Add the proper noun, chat log, sentence context, and proper noun type to the database
                data[i] = append_hit_data(data[i],"Proper noun",entity.text.lower(), str(line[entity.start - 5:entity.end + 5]), patron_or_op, entity.label_)
        i += 1
    return data

def initialize_query_return_data(terms):
    """
    Perform a modification to the list of terms, allowing it to be accessed easily
    Parameters:
        terms: A list of lists, each containing a term to search for in the 0th index
    Returns:
        terms: A list of strings, each containing a term to search for
    """
    for i in range(len(terms)):
        terms[i] = terms[i][0]
    return terms

def strip_punctuation(text):
    """
    Remove punctuation and spaces from a queryed course code or term.
    Parameters:
        text: The text to strip punctuation and spaces from.
    Returns:
        text: The stripped text
    """
    if text[0] == ' ':
        text = text[1:]
    if text[-1] in ' .':
        text = text[:-1]
    return text

def query(chat_log, line, terms, chat_id, line_index):
    """
    Perform required querying tasks on a chat log
    Parameters:
        chat_log: A chat log list
        line: A list where each object is a string containing a word
        terms: A list of terms to query
        chat_id: The identification number of the chat log
        line_index: The index of the message to be observed in the chat log
    Returns:
        chat_log: A chat log list with all query data appended
    """
    line_string = line_to_string(line)
    #Remove user data if in ask chat mode
    trimmed_line_string = line_to_string(line[2:]) if MODE == "ask_chat" else line_string
    lower = trimmed_line_string.lower()
    #Ignore most common system messages
    if "System message:" not in line_string and "ask a librarian" not in lower:
        #Check for terms
        for term in terms:
            if term != "Utsc.utoronto.ca" and term != "Utoronto.ca":
                term_search = re.search("(^| )" + term.lower() + "($| |\.)", lower )
                if term_search:
                    chat_log = append_hit_data(chat_log,"Query term",term,line_string, patron_or_operator(chat_log, line_index))
            elif term.lower() in lower:
                chat_log = append_hit_data(chat_log,"Query term",term,line_string, patron_or_operator(chat_log, line_index))
        #Check for with specific requirements or terms that need to be grouped together under one name
        if " librar" in lower:
            chat_log = append_hit_data(chat_log,"Query term","Library",line_string, patron_or_operator(chat_log, line_index))
        if " nvivo" in lower or " nvivohub" in lower:
            chat_log = append_hit_data(chat_log,"Query term","Nvivo",line_string, patron_or_operator(chat_log, line_index))
        if " reference" in lower:
            chat_log = append_hit_data(chat_log,"Query term","Reference",line_string, patron_or_operator(chat_log, line_index))
        if " citation" in lower:
            chat_log = append_hit_data(chat_log,"Query term","Citation",line_string, patron_or_operator(chat_log, line_index))
        if " protocol" in lower:
            chat_log = append_hit_data(chat_log,"Query term","Library",line_string, patron_or_operator(chat_log, line_index))
        #Check if a form of the word "Graduate" is in the line - but it isn't a form of "undergraduate" or "graduated"
        if " grad " in lower or " gradu" in lower:
            chat_log = append_hit_data(chat_log,"Query term","Graduate",line_string, patron_or_operator(chat_log, line_index))
        #Check if master's is mentioned
        if re.search(" M\.{0,1}A(\n| )", line_string) or re.search(" master'{0,1}s(\n| )",lower):
            chat_log = append_hit_data(chat_log,"Query term","Master's",line_string, patron_or_operator(chat_log, line_index))
        #Check if MSC is mentioned
        if re.search("(^| )((M\.{0,1}Sc)|(m\.{0,1}sc)|(M\.{0,1}sc))($| |\.)", line_string):
            chat_log = append_hit_data(chat_log,"Query term","MSC",line_string, patron_or_operator(chat_log, line_index))
        #Check if there is a file extension
        file_extension_match = re.search("[^/.]\.([a-z]{2,5})(?<!\.com)(?<!\.co)(?<!\.ca)(?<!\.org)(?<!\.or)(?<!\.net)(?<!\.ne)(?<!\.gov)(?<!\.go)(?<!\.edu)(?<!\.ed)(?<!\.html)(?<!\.htm)(?<!\.ht) ", line_string)
        if file_extension_match:
            chat_log = append_hit_data(chat_log,"File Extension",file_extension_match.group()[1:-1],line_string, patron_or_operator(chat_log, line_index))
        #Check if course code(^| )(([A-Za-z]{3}\d{3})|([A-Za-z]{3}(A|B|C|D|a|b|c|d)\d{2}))((H|Y|h|y)\d){0,1}
        course_code_match = re.search("(^| )(([A-Za-z]{3}\d{3})|([A-Za-z]{3}(A|B|C|D|a|b|c|d)\d{2}))((H|Y|h|y)\d){0,1}(f|s|y|F|S|Y){0,1}($| |\.)", line_string)
        if course_code_match:
            chat_log = append_hit_data(chat_log,"Course Code",strip_punctuation(course_code_match.group()),line_string, patron_or_operator(chat_log, line_index))
    return chat_log

def iterate_query(data, terms):
    """
    Perform required querying tasks iteratively.
    Parameters:
        data: The list containing all data to analyze
        terms: A list of terms to query
    Returns:
        data: The list containing all data to analyze, with all chat logs queried and added as hits
    """
    for i in range(len(data)): #Iterate over each chat log
        for j in range(len(data[i][data_array_text_location])): #Iterate over each line
            if len(data[i][data_array_text_location][j]) > 1:
                #Perform sentence queries
                data[i] = query(data[i], data[i][data_array_text_location][j], terms, data[i][0], j)
    return data

def export_csv(data, headers, name):
    """
    Export relevant data in a .csv format. Remove any data that may contain private information.
    Paramters:
        data: The list containing all data to analyze
        headers: A list of all column headers
        name: The filename to export as
    """
    with open(name, 'w') as csvfile:
        writer = csv.writer(csvfile)

        if MODE == "ask_chat":
            writer.writerow(["id", "guest", "protocol", "queue", "profile", "started", "wait", "duration", "referrer", "referrer domain", "Operator Institution", "UofT Operator Role", "UofT Operator Campus", "Redacted?", "Notes", "Hit Type", "Hit", "Hit Context", "Sent by", "Proper noun classification"])
            names = convertcsv("names.csv")[0]
            for chat_log in data:
                #If there are no hits for a chat, just output one row containing all metadata for that chat
                if len(chat_log[len(chat_log) - 5]) == 0:
                    row = chat_log[:len(chat_log) - 5]
                    row.pop(11) #Remove text
                    row.pop(9) #Remove ip
                    row.pop(8) #Remove operator
                    for i in range(6):
                        row.append("")
                    row.append("No hit!")
                    for i in range(4):
                        row.append("")
                    writer.writerow(row)
                else:
                    for i in range(len(chat_log[len(chat_log) - 5])): #Iterate over each hit
                        row = chat_log[:len(chat_log) - 5]
                        row.pop(11) #Remove text
                        row.pop(9) #Remove ip
                        row.pop(8) #Remove operator
                        if i > 0: #Remove id if not a unique log, so we can differentiate between unique logs easily
                            row[0] = ""
                        #Add operator data
                        row.append(get_referrer_domain(chat_log[10]))
                        row.append(get_operator_institution(chat_log[8]))
                        operator_data = get_operator_data(chat_log[8], names)
                        row.append(operator_data[0])
                        row.append(operator_data[1])
                        row.append("")
                        row.append("")
                        #Add all hit data
                        row.append(chat_log[len(chat_log) - 5][i])
                        row.append(chat_log[len(chat_log) - 4][i])
                        row.append(chat_log[len(chat_log) - 3][i])
                        row.append(chat_log[len(chat_log) - 2][i])
                        row.append(chat_log[len(chat_log) - 1][i])

                        writer.writerow(row)
        if MODE == "jira":
            writer.writerow(["Summary", "Issue key", "Issue id", "Issue Type", "Status", "Project key", "Project name", "Project type", "Project url", "Priority", "Resolution", "Created", "Updated", "Last Viewed", "Resolved", "Redacted?", "Notes", "Hit Type", "Hit", "Hit Context", "Proper noun classification"])
            for chat_log in data:
                for i in range(len(chat_log[len(chat_log) - 1])): #Iterate over each hit
                    row = []
                    row.append(chat_log[headers.index("Summary")])
                    row.append(chat_log[headers.index("Issue key")])
                    if i > 0:
                        row.append("")
                    else:
                        row.append(chat_log[headers.index("Issue id")])
                    row.append(chat_log[headers.index("Issue Type")])
                    row.append(chat_log[headers.index("Status")])
                    row.append(chat_log[headers.index("Project key")])
                    row.append(chat_log[headers.index("Project name")])
                    row.append(chat_log[headers.index("Project type")])
                    row.append(chat_log[headers.index("Project url")])
                    row.append(chat_log[headers.index("Priority")])
                    row.append(chat_log[headers.index("Resolution")])
                    row.append(chat_log[headers.index("Created")])
                    row.append(chat_log[headers.index("Updated")])
                    row.append(chat_log[headers.index("Last Viewed")])
                    row.append(chat_log[headers.index("Resolved")])
                    row.append("")
                    row.append("")
                    row.append(chat_log[len(chat_log) - 5][i])
                    row.append(chat_log[len(chat_log) - 4][i])
                    row.append(chat_log[len(chat_log) - 3][i])
                    row.append(chat_log[len(chat_log) - 1][i])
                    writer.writerow(row)

#Take the file from filename, run querying and processing, and add its data to return_data.
def add_file_data(filename, terms, return_data, export_filename=None):
    """
    For a given file, analyze it for hits and add its data to return data. If export_filename has a value, then export the data as a .csv file.
    Parameters:
        filename: The name of the file to read data from.
        terms: A list containing each term to query for.
        return_data: A list of previously analyzed data to add this data to.
        export_filename: If this variable has a value, then export the data as this filename.
    Return:
        return_data: A list containing all data that has been analyzed, including data from filename.
    """
    #Get headers and data
    print("Analyzing file", filename)
    data = convertcsv(filename)
    headers = data[1]
    data = data[0]
    #Split sentences
    if MODE == "jira":
        get_jira_data_array_text_location(headers)
    data = split_sentences(data)

    start = time.process_time()
    #Search for query terms
    data = iterate_query(data, terms)
    print("Querying took", time.process_time() - start, "seconds")
    #Search for proper nouns
    start = time.process_time()
    data = analyze_proper_nouns(data)
    print("Analyzing proper nouns took", time.process_time() - start, "seconds")
    #Add data to return_data
    for row in data:
        return_data.append(row)
    #Export if export_filename has a value
    if export_filename:
        export_csv(return_data, headers, export_filename)
    return return_data

def main():
    terms = convertcsv('text_terms_DS.txt')[0]
    terms = initialize_query_return_data(terms)

    data = []
    if len(sys.argv) > 3:
        if sys.argv[1] != "ask_chat" or sys.argv[1] != "jira":
            global MODE
            MODE = sys.argv[1]
        else:
            print("Please enter a recognized mode: ask_chat or jira.")
            exit(2)
        for i in range(2, len(sys.argv) -1):
            if i == len(sys.argv) - 2:
                data = add_file_data(sys.argv[i], terms, data, sys.argv[len(sys.argv) -1])
            else:
                data = add_file_data(sys.argv[i], terms, data)
    else:
        print("Please enter the mode, at least one .csv file to analyze, and output file name.")
        exit(1)
    print("done")

if __name__ == "__main__":
    main()
