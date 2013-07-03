import re, nltk

#
# Use the same tokenization as JSTOR
# see https://github.com/ITHAKA-AT/ejc-mapreduce/blob/master/ngrams.py
#

#Helper function to generate ngrams from raw text using NLTK ngram generator
def generate_ngrams(raw_text, n=1):
    tokenized_sentences = get_tokenized_sentences(raw_text)
    grams = {}
    for tokens in tokenized_sentences:
        if n == 1:
            for gram in tokens:
                if gram.isalpha():
                    grams[(gram,)] = grams.get((gram,),0) + 1
        else:
            for gram in nltk.ngrams(tokens, n):
                grams[gram] = grams.get(gram,0) + 1
    sorted_grams = []
    for gram, count in grams.items():
        sorted_grams.append([' '.join(gram), count])
    sorted_grams.sort(lambda y, x: cmp(x[1],y[1]))
    return sorted_grams


#Tokenize our text input using NLTK tokenizer.
#We're not calling this directly, but rather letting generate_ngrams() call it for us.
#note that some special tokens are inserted for sentence start/end, numbers are converted to a single token, punctuation is reduced to fewer tokens
#if you wanted to apply stemming, spell checking, etc, this is probably where you'd do it.  NLTK provides a lot of this type of functionality.
def get_tokenized_sentences(raw_text):
    tokenized_sentences = []
    if raw_text:
        # normalize whitespace
        raw_text = re.sub('\s+', ' ', raw_text)
        raw_text = re.sub('-\s+', '', raw_text)
    for sentence in nltk.tokenize.sent_tokenize(raw_text):
        tokens = ['#SENTENCE_START#']
        for token in sentence.lower().replace('.','').split(' '):
            if token:
                if (token.isalpha()):
                    tokens.append(token)
                elif token.isdigit():
                    tokens.append('#NUMBER#')
                else:
                    tokens.append('#NON_ALPHANUM#')
        tokens.append('#SENTENCE_END#')
        tokenized_sentences.append(tokens)
    return tokenized_sentences
