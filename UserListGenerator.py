#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wikipedia, re, string

RE_USER = re.compile('\[\[[Uu]ser ?: ?(.*?) ?[\|\]]')
RE_LISTED = re.compile(' *[\*#] *(.+?)\W')
RE_RIBBONBEARER = re.compile('\{\{.*?name ?= ?(?:\[\[[Uu]ser:)?(.*?) ?[\|\}]')

improbablenames = ["and", "i", "we"]

def fuzzyadd(a,b): #combine two fuzzy values
  return (a+b)/2.0
  #return sqrt(a*a+b*b)

debug_fuzz = None
def getDebugFuzz():
  global debug_fuzz
  return debug_fuzz

def normalize(dic):
  maxfuzz = 0
  for p,v in dic.items():
    if v>maxfuzz:
      maxfuzz=v
  if maxfuzz>0:
    for p,v in dic.items():
      dic[p]=v/maxfuzz
  return dic

def unscorify(word):
  return word.replace("_"," ")

def identifyParticipants(text, page):
  global debug_fuzz
  fuzzy = {} #user id -> probability of being a participant

  if "[[Category:Not reached - Did not attempt]]" in text:
    return []

  sections = getSection(text, ("participant", "participants", "people", "participant?", "participants?", "people?", "attendees", "attendees?", "the people", "adventurers"))
  if sections:
    linked = map(unscorify, RE_USER.findall(sections))
    for part in linked:
      fuzzy[part]=10.0; 
    #extract non user:-linked users from a list of participants
    linked = map(unscorify, RE_LISTED.findall(sections))
    for part in linked:
      if not "[" in part: 
        fuzzy[part]=10.0;
  else:
    linked = map(unscorify,RE_USER.findall(text))
    for part in linked:
      fuzzy[part]=fuzzy.get(part,0)+1.0;

  mentions = {}
  mcount   = 0.0
  for p in fuzzy.keys():
    mentions[p] = len(re.findall(re.escape(p), text, re.IGNORECASE))
    mcount += mentions[p]
  if mcount>0:
    for p,v in mentions.items():
      #print p,v*v/mcount
      fuzzy[p]=fuzzyadd(fuzzy[p],v*v/mcount)

  #identify all ribbon bearers
  linked = RE_RIBBONBEARER.findall(text)
  for part in linked:
    part = part.split(",")
    for ppart in part:
      ppart = ppart.split(" and ")    
      for pppart in ppart:
        pppart = pppart.strip()
        fuzzy[pppart]=fuzzyadd(fuzzy.get(pppart,1),5);

  if len(fuzzy)==0: #only if we still don't have fuzz
    history = page.getVersionHistory()
    #compare the edit history with the page content
    editors = [change[2] for change in history]
    for editor in editors:
      if editor.lower() in text.lower():
        fuzzy[editor]=0.5

  #print fuzzy

  fuzzy = normalize(fuzzy)

  participants = []
  for p,v in fuzzy.items():
    if p in improbablenames:
      v = fuzzyadd(v,-1)
    if v>=0.35:
      participants.append(p)
  

  debug_fuzz = fuzzy
  return participants
  
def getUsers(page):
  """
returns a list of expeditions participants found in the text of a geohashing expedition page.
ingredients: one wikipedia.Page object
  """
  text = page.get()
  title = page.title()
  wikipedia.output(u'Parsing %s...' % title)

  if(text[0] == u"="):  # a hack?
    text = u"\n" + text

  if(text[1] == u"="):
     text = u"\n" + text

#Generate the list of people
#First look in appropriately named "who" sections
  peopleSecText = getSection(text, ("participant", "participants", "people", "participant?", "participants?", "people?"))
  if(peopleSecText != None):
    peopleText = getPeopleText(text, peopleSecText)

#If that fails, look for all unique [[User:*]] tags in the expedition page
  if((peopleSecText == None) or (len(peopleText) == 0)):
    peopleText = getUserList(text)

  return peopleText

def getSections(text):
   text_arr = re.split("=+(.*?)=+", text)
   for i in range(0,len(text_arr)):
       text_arr[i] = string.strip(text_arr[i])

   section_hash = {}
   section_hash[""] = text_arr[0]

   for i in range(1,len(text_arr),2):
     title = string.lower(text_arr[i])
     section_hash[title] = section_hash.get(title,"") + text_arr[i+1]

   return section_hash

def getSection(text, name_arr):
  """
This will look for a section with one of the names in name_arr
The search is case insensitive, and returns the first match, starting from name_arr[0] and continuing to name_arr[len(name_arr)-1]
It will return the body of the appropriate section, or None if there were no matches for the section name.
  """
  sections = getSections(text)
  code = ""
  for header in name_arr:
      if header in sections:
          code += sections[header] +"\n"
  if ((len(name_arr) == 0) and ("" in sections)):
      return sections[""]
  if len(code)>0:
    return code
  return None

def getUserUist(text):
  """This will look for all unique user tags on a page, and make a list out of them."""
  regex_res = re.findall("\[\[User:.*?\]\]", text, re.I)
  regex_lower = []
  for i in range(0,len(regex_res)):
    regex_lower.append(re.sub("_", " ", regex_res[i].lower()))
    regex_lower[i] = re.sub(" ?| ?", "|", regex_lower[i])
    regex_lower[i] = re.sub("'s", "", regex_lower[i])
  result_arr = []
  for i in range(0,len(regex_lower)):
    for j in range(i+1,len(regex_lower)):
      if (regex_lower[i] == regex_lower[j]):
        break
      else:
        result_arr.append(regex_res[i])

  temp_str = u", "
  return temp_str.join(result_arr)

def getPeopleText(text, people_text):
  """This function will parse a list of users, and return them in a comma separated list."""
  people_text = re.sub("<!--.*?(-->|$)", "", people_text)
  people_text = string.strip(re.sub("^\[[^][]*?\]", "", people_text))
  people_text_arr = re.split("\n", people_text)

  people_text = u""

  if (len(people_text_arr[0]) == 0):
    people_regex_str = re.compile("^(\[\[.*?\]\]|[^ ]*)")
  elif (people_text_arr[0][0] == "*"):
    people_regex_str = re.compile("^\*\s*(\[\[.*?\]\]|[^ ]*)")
  elif (people_text_arr[0][0] == ":"):
    people_regex_str = re.compile("^:\s*(\[\[.*?\]\]|[^ ]*)")
  else:
    people_regex_str = re.compile("^(\[\[.*?\]\]|[^ ]*)")

  match_obj = people_regex_str.match(people_text_arr[0])
  people_text += match_obj.group(1)

  if(re.match("=", people_text_arr[0])):
    people_text = getUserList(text)
  else:
    for i in range(1,len(people_text_arr)):
      match_obj = people_regex_str.match(people_text_arr[i])
      if ((match_obj != None) and (len(match_obj.group(1)) != 0)):
        if(re.search("Category", people_text_arr[i])):
          pass
        elif (re.match("=", people_text_arr[i])):
          pass
        else:
          people_text += u", "
          people_text += match_obj.group(1)
  return people_text