import spacy
import re
import string
from fuzzywuzzy import fuzz
from .domains import DOMAINS
from .reviewers import REVIEWERS

nlp = spacy.load("en_core_web_trf")

def normalize_text(text):
    doc = nlp(text.lower())
    tokens = [token.lemma_ for token in doc if token.text not in string.punctuation]
    return " ".join(tokens)

def fuzzy_match(text1, text2, threshold=80):
    ratio = fuzz.ratio(text1, text2)
    return ratio >= threshold

def extract_keywords(text):
    doc = nlp(text)
    keywords = set()
    for ent in doc.ents:
        keywords.add(ent.text.strip())
    for chunk in doc.noun_chunks:
        keywords.add(chunk.text.strip())
    return list(keywords)

def map_keywords_to_domains(keywords):
    matched_domains = {}
    normalized_keywords = [normalize_text(kw) for kw in keywords]
    for domain, subfields in DOMAINS.items():
        for subfield in subfields:
            norm_subfield = normalize_text(subfield)
            for kw in normalized_keywords:
                if norm_subfield in kw or kw in norm_subfield or fuzzy_match(norm_subfield, kw):
                    matched_domains.setdefault(domain, set()).add(subfield)
    return {domain: list(s) for domain, s in matched_domains.items()}

def assign_reviewers(matched_domains):
    assignments = {}
    for domain, subfields in matched_domains.items():
        eligible = set()
        norm_subfields = [normalize_text(sf) for sf in subfields]
        for reviewer in REVIEWERS:
            for interest in reviewer.get("interests", []):
                norm_interest = normalize_text(interest)
                for nsf in norm_subfields:
                    if nsf in norm_interest or norm_interest in nsf or fuzzy_match(nsf, norm_interest):
                        eligible.add(reviewer["name"])
                        break
        assignments[domain] = list(eligible)
    return assignments

def get_detailed_reviewer_profiles(reviewer_names):
    return [reviewer for reviewer in REVIEWERS if reviewer["name"] in reviewer_names]
