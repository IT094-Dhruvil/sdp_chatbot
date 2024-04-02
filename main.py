import PyPDF2
import nltk
import string
import random


# Open the PDF file in binary mode
pdfFileObj = open("C:\\Users\\dhruv\\OneDrive\\Desktop\\IT_final1.pdf", 'rb')
pdfReader = PyPDF2.PdfReader(pdfFileObj)

# Accumulate text from all pages
raw_data = ''
for page_number in range(len(pdfReader.pages)):
    pageObj = pdfReader.pages[page_number]
    raw_data += pageObj.extract_text()


raw_doc = raw_data.lower()


nltk.download('punkt')  # tokenizer
nltk.download('wordnet')  # using the dictionary



# Tokenize the text
sentence_tokens = nltk.sent_tokenize(raw_doc)
word_tokens = nltk.word_tokenize(raw_doc)

# Lemmatize the tokens
lemmatizer = nltk.stem.WordNetLemmatizer()

def LemTokens(tokens):
    return [lemmatizer.lemmatize(token) for token in tokens]

remove_punc_dict = dict((ord(punct), None) for punct in string.punctuation)

def LemNormalize(text):
    return LemTokens(nltk.word_tokenize(text.lower().translate(remove_punc_dict)))

# Greeting responses
greet_inputs = ('hi', "hello", 'whatsupp', 'how are you?')
greet_responses = ('hi', "hello", 'hey there', 'there there!!')

def greet(sentence):
    for word in sentence.split():
        if word.lower() in greet_inputs:
            return random.choice(greet_responses)

# Import necessary libraries for response generation
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Generate response
def response(user_response):
    robo1_response = ''
    TfidVec = TfidfVectorizer(tokenizer=LemNormalize, stop_words='english')
    tfidf = TfidVec.fit_transform(sentence_tokens)
    vals = cosine_similarity(tfidf[-1], tfidf)
    idx = vals.argsort()[0][-2]
    flat = vals.flatten()
    flat.sort()
    req_tfidf = flat[-2]
    if req_tfidf == 0:
        robo1_response = robo1_response + "I am sorry. Unable to understand you!"
        return robo1_response
    else:
        robo1_response = robo1_response + sentence_tokens[idx]
        return robo1_response

# Main loop for conversation
flag = True

print("Hello! I am the retrieval bot. Start typing your greeting to talk to me. For ending the conversation, type 'bye'")
while flag:
    user_response = input("You: ")
    user_response = user_response.lower()
    if user_response != 'bye':
        if user_response == 'thank you' or user_response == 'thanks':
            flag = False
            print("Bot: You are welcome!!")
        else:
            sentence_tokens.append(user_response)
            word_tokens = word_tokens + nltk.word_tokenize(user_response)
            final_words = list(set(word_tokens))
            print('Bot:', end=' ')
            print(response(user_response))
            sentence_tokens.remove(user_response)
    else:
        flag = False
        print("Goodbye!!")
