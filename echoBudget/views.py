from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404
from django.urls import reverse

from echoBudget.forms import ExpenseForm, DateSelectionForm
from echoBudget.models import Expense, Category

import datetime, json
import speech_recognition as sr
import calendar, time
import spacy

from gtts import gTTS
import threading, copy
import os, math
import numpy as np

nlp = spacy.load("en_core_web_sm")
module_dir = os.path.dirname(__file__)
nlp_path = os.path.join(module_dir, 'model-best')
word2vec_path = os.path.join(module_dir, 'glove.6B.100d.txt')
nlp_customized = spacy.load(nlp_path)


data = {
    'Food': ['fruit', 'noodle', 'dinner', 'pizza', 'restaurant', 'sandwich', 'snack', 'vegetable', 'milk', 'alcohol', 'seasoning', 'lunch'],
    'Housing': ['house', 'rent', 'utility', 'hotel'],
    'Necessities': ['soap', 'laptop', 'clothes', 'medicine', 'bag', 'phone'],
    'Transportation': ['bus', 'uber', 'taxi', 'metro', 'gas'],
    'Entertainment': ['game', 'video', 'sport', 'book', 'subscription', 'movie', 'trip', 'museum']
}

word_cat = {word: key for key, words in data.items() for word in words}
embeddings = {}
with open(word2vec_path) as f:
    for line in f:
        values = line.split()
        word = values[0]
        vector = np.array(values[1:], dtype=np.float32)
        embeddings[word] = vector
existing_embed = {key: value for key, value in embeddings.items() if key in word_cat.keys()}

def add_item(name, category):
    if category not in data.keys():
        return
    if name not in embeddings.keys():
        word_cat[name] = category
        return
    if name in word_cat.keys():
        c = word_cat[name]
        data[c].remove(name)
    existing_embed[name] = embeddings[name]
    word_cat[name] = category
    data[category].append(name)

# Returns category as a string
def classify(name): 
    name = name.lower()
    if name in word_cat.keys():
        return word_cat[name]
    if name not in embeddings.keys():
        return "Others"
    name_vector = embeddings[name]
    scores = {}
    for word, vector in existing_embed.items():
        cate = word_cat[word]
        distance = name_vector.dot(vector) / len(data[cate])
        scores[cate] = scores.get(cate, 0) + distance
    scores["Others"] = 6
    return max(scores, key=scores.get)

# Create your views here.
def home_action(request):
    context = {'active' : 'home'}
    if 'message' in request.session:
        # display the message and delete it in request.session
        message = request.session['message']
        context['message'] = message
        del request.session['message']
    if request.method == "GET":
        form = ExpenseForm()
        context['form'] = form
    elif request.method == "POST":
        form = ExpenseForm(request.POST)
        if not form.is_valid():
            print("form not valid")
            context = {'message': "Invalid Form"}
            return render(request, 'echobudget/home.html', context)
        try:
            cate = Category.objects.get(id=form.cleaned_data['category'])
        except:
            context = {'message': 'Invalid category'}
            return render(request, 'echobudget/home.html', context)
        expense = Expense(date = datetime.datetime.now(),
                          amount = form.cleaned_data['amount'],
                          item_name = form.cleaned_data['item_name'],
                          category = cate)
        expense.save()
        request.session['message'] = 'Entry saved'
        context['form'] = ExpenseForm()
    return render(request, 'echobudget/home.html', context)

def entry_filter(start_date, end_date):
    result = Expense.objects.filter(date__range=[start_date, end_date])
    return result

def list_action(request):
    context = {'active': 'record'}
    if 'message' in request.session:
        # display the message and delete it in request.session
        message = request.session['message']
        context['message'] = message
        del request.session['message']
    # handles GET request to list page
    if request.method == "GET":
        today = datetime.datetime.now()
        # get first and last dates of this month
        start_date = datetime.datetime(today.year, today.month, 1)
        first_day_next_month = datetime.datetime(today.year + today.month // 12, 
            today.month % 12 + 1, 1)
        end_date = first_day_next_month - datetime.timedelta(days=1)
        entries = entry_filter(start_date, end_date)
        start_date = start_date.strftime("%Y-%m-%d")
        end_date = end_date.strftime("%Y-%m-%d")
        initial_data = {'start_date': start_date, 'end_date': end_date}
        form = DateSelectionForm(initial_data)
        context = {'form': form, 'entries': entries, 'active': 'record'}
        return render(request, 'echobudget/record.html', context)
    elif request.method == "POST":
        form = DateSelectionForm(request.POST)
        if not form.is_valid():
            print("form not valid")
            context = {'message': "Invalid Form"}
            return render(request, 'echobudget/record.html', context)
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        entries = entry_filter(start_date, end_date)
        context = {'form': form, 'entries': entries, 'active': 'record'}
        return render(request, 'echobudget/record.html', context)

def get_report_data(labels, entries):
    entries_num = []
    for c in labels:
        cate_object = Category.objects.get(name=c)
        cur_entries = entries.filter(category=cate_object)
        price = 0
        for e in cur_entries:
            price += float(e.amount)
        entries_num.append(price)
    total = sum(entries_num)
    if total == 0: 
        data = [0 for _ in range(len(entries_num))]
    else:
        data = [num/total for num in entries_num]
    return data

def report_action(request):
    categories = Category.objects.values_list('name', flat=True)
    labels = [c for c in categories]
    form = None
    if request.method == "GET":
        today = datetime.datetime.now()
        # get first and last dates of this month
        start_date = datetime.datetime(today.year, today.month, 1)
        first_day_next_month = datetime.datetime(today.year + today.month // 12, 
            today.month % 12 + 1, 1)
        end_date = first_day_next_month - datetime.timedelta(days=1)
        start_date = start_date.strftime("%Y-%m-%d")
        end_date = end_date.strftime("%Y-%m-%d")
        initial_data = {
            'start_date': start_date,
            'end_date': end_date,
        }
        form = DateSelectionForm(initial_data)
        entries = entry_filter(start_date, end_date)
    elif request.method == "POST":
        form = DateSelectionForm(request.POST)
        if not form.is_valid():
            print("form not valid")
            context = {'message': "Invalid Form"}
            return render(request, 'echobudget/report.html', context)
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        entries = entry_filter(start_date, end_date)
    data = get_report_data(labels, entries)
    context = {'form': form, 'active': 'report', 'labels': labels, 'data': data}
    return render(request, 'echobudget/report.html', context)

def audio_report_helper(page, date):
    try:
        if len(date) == 0: 
            today = datetime.datetime.now()
            # get first and last dates of this month
            start_date = datetime.datetime(today.year, today.month, 1)
            first_day_next_month = datetime.datetime(today.year + today.month // 12, 
                today.month % 12 + 1, 1)
            end_date = first_day_next_month - datetime.timedelta(days=1)
            start_date = start_date.strftime("%Y-%m-%d")
            end_date = end_date.strftime("%Y-%m-%d")
        elif "to" not in date:
            parsed_data = datetime.datetime.strptime(date.strip(), "%B %Y")
            start_date = parsed_data.strftime("%Y-%m-01")
            tmp_end_date = start_date.split("-")
            end_year, end_month = tmp_end_date[0], tmp_end_date[1]
            num_days = calendar.monthrange(int(end_year), int(end_month))
            end_date = end_year + "-" + end_month + "-" + str(num_days[1])
        else:
            dates = date.strip().split("to")
            parsed_list = []
            for d in dates:
                parsed_data = datetime.datetime.strptime(d.strip(), "%B %Y")
                parsed_list.append(parsed_data)
            start_date = parsed_list[0].strftime("%Y-%m-01")
            end_date = parsed_list[1].strftime("%Y-%m")
            tmp_end_date = end_date.split("-")
            end_year, end_month = tmp_end_date[0], tmp_end_date[1]
            num_days = calendar.monthrange(int(end_year), int(end_month))
            end_date = end_date + "-" + str(num_days[1])
    except:
        t = threading.Thread(target=play_output, args=["i try again",])
        t.setDaemon(False)
        t.start()
        return {'message': 'Try again', 'active': page, 'form': DateSelectionForm()}
    entries = entry_filter(start_date, end_date)
    initial_data = {
        'start_date': start_date,
        'end_date': end_date,
    }
    form = DateSelectionForm(initial_data)
    context = {}
    if page == "report":
        categories = Category.objects.values_list('name', flat=True)
        labels = [c for c in categories]
        data = get_report_data(labels, entries)
        context = {'form': form, 'active': 'report', 'labels': labels, 'data': data}
        output = "i "
        for i in range(len(labels)):
            label = labels[i]
            percentage = str(math.floor(data[i] * 100)) + "percent"
            output += label + " " + percentage + ", "
        t = threading.Thread(target=play_output, args=[output,])
        t.setDaemon(False)
        t.start()
    if page == "record":
        output = "i "
        for e in entries:
            output += "Number " + str(e.id) + " " + e.item_name + " " + str(e.amount) + " dollars " + e.category.name + ", "
        output += "you can say modify or remove number ten, for example, to modify or remove that entry."
        t = threading.Thread(target=play_output, args=[output,])
        t.setDaemon(False)
        t.start()
        context = {'form': form, 'entries': entries, 'active': 'record'}
    return context

def audio_enter_helper(request, page, params):
    item = params["item"]
    price = params["price"]
    if len(item) == 0 or len(price) == 0:
        return {'message': 'missing information', 'active': page}
    category = classify(item)
    print(category)
    p = params['price'].split(' ')[0].strip('$')
    real_price = round(float(p), 2)
    try:
        real_category = Category.objects.get(name=category)
        initial_data = {'item_name': item, 'amount': real_price, 'category': real_category.id}
        form = ExpenseForm(initial_data)
        request.session['form'] = initial_data
        output = "i Entering " + item + " for " + price + " dollars as " + category + ", please press the speaking button and confirm"
        t = threading.Thread(target=play_output, args=[output,])
        t.setDaemon(False)
        t.start()
        return {'form': form, 'active': page}
    except:
        return {'message': 'no such category', 'active': page}
    

def play_output(to_read):
    tts = gTTS(to_read)
    tts.save("output.mp3")
    os.system("mpg321 output.mp3")
    os.remove("output.mp3")

def parse_change(text_output, params):
    text_output = text_output.replace("change ", "")
    elems = text_output.split(" to ")
    try:
        label, value = elems[0].strip(), elems[1].strip()
        params['label'] = label
        if 'price' in label and not params['price'] and not params['num']:
            params['error'] = "try again"
        if 'category' in label:
            categories = Category.objects.values_list('name', flat=True)
            cat_list = [c for c in categories]
            value = value[0].upper() + value[1:]
            if value not in cat_list:
                params['error'] = "no such category"
            else:
                params['category'] = value
        if 'item name' in label:
            if value:
                params['item'] = value
            else:
                params['error'] = 'Try again'
        return params
    except:
        params['error'] = "try again"
        return params

def speak_action(request):
    if request.method == "POST":
        r = sr.Recognizer()
        params = {
            "action": "",
            "date": "",
            "price": "",
            "item": "",
            "error": "",
            "num": "",
            "category": "",
        }
        num_dict = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        }
        try:
            tts = gTTS("istart recording")
            tts.save("start.mp3")
            os.system("mpg321 start.mp3")
            with sr.Microphone() as source:

                audio = r.listen(source, 15, 6)
   
            text_output = r.recognize_google(audio)
            print(text_output)
            doc = nlp(text_output)
            doc_customized = nlp_customized(text_output)
            for token in doc:
                print(token.pos_, token.text)
                if (token.pos_ == "VERB") and not params["action"]:
                    params["action"] = token.text
            print("before: ", params)
            for ent in doc.ents:
                if (ent.label_ == "DATE"): # month year to month year
                    params["date"] = ent.text
                if (ent.label_ == "MONEY"): # $5 // 5 dollars
                    params["price"] = ent.text
                if (ent.label_ == "CARDINAL"):
                    num = ent.text
                    if num in num_dict:
                        params["num"] = num_dict[num]
                    else:
                        params["num"] = int(num)
            print("default model", params)
            for ent in doc_customized.ents:
                print(ent.label_, ent.text)
                if (ent.label_ == "ACTION") and ("change" in ent.text):
                    params["action"] = ent.text
                    return parse_change(text_output, params)
                if (ent.label_ == "ACTION") and len(params["action"]) == 0:
                    params["action"] = ent.text
                if (ent.label_ == "ITEM"):
                    params["item"] = ent.text
            print(params)
            return params
            
        except sr.WaitTimeoutError:
            params["error"] = "Try again one"
            return params
        except ValueError:
            params["error"] = "Try again two"
            return params
        except sr.UnknownValueError:
            params["error"] = "Try again three"
            return params

def parse_verb(request, params):
    if "enter" in params["action"]:
        context = audio_enter_helper(request, 'home', params)
        return render(request, 'echobudget/home.html', context)
    if "get" in params["action"]:
        context = audio_report_helper('record', params["date"])
        return render(request, 'echobudget/record.html', context)
    if "generate" in params["action"]:
        context = audio_report_helper('report', params["date"])
        return render(request, 'echobudget/report.html', context)
    if "help" in params["action"]:
        # output = "i Press the right half of the screen to start recording. Wait 1 second after you hear start recording to speak. To enter a new spending, say enter apple for 5 dollars for example. To get all entries, say get entries. To generate report, say generate report. "
        os.system("mpg321 help.mp3")
        form = ExpenseForm()
        context = {'form': form, 'active': 'home'}
        return render(request, 'echobudget/home.html', context)
    else:
        return None

def speak_report_action(request):
    params = speak_action(request)
    if len(params["error"]) != 0:
        form = DateSelectionForm()
        t = threading.Thread(target=play_output, args=["i Try again",])
        t.setDaemon(False)
        t.start()
        return render(request, 'echobudget/report.html', {"message": params["error"], "active": "report", "form": form})
    page = parse_verb(request, params)
    if page:
        return page
    form = DateSelectionForm()
    context = {'message': 'Action not supported', 'active': 'report', 'form': form}
    t = threading.Thread(target=play_output, args=["action not supported",])
    t.setDaemon(False)
    t.start()
    return render(request, 'echobudget/report.html', context)

def speak_home_action(request):
    params = speak_action(request)
    if len(params["error"]) != 0:
        form = ExpenseForm()
        t = threading.Thread(target=play_output, args=[params['error'],])
        t.setDaemon(False)
        t.start()
        return render(request, 'echobudget/home.html', {"message": params["error"], "active": "home", "form": form})
    page = parse_verb(request, params)
    if page:
        return page
    if "confirm" in params["action"]:
        context = {'active': 'home'}
        initial_data = request.session.get('form')
        del request.session['form']
        form = ExpenseForm(initial_data)
        if not form or not form.is_valid():
            print("form not valid")
            context = {'message': "Invalid Form"}
            return render(request, 'echobudget/home.html', context)
        try:
            cate = Category.objects.get(id=form.cleaned_data['category'])
        except:
            context = {'message': 'Invalid category'}
            return render(request, 'echobudget/home.html', context)
        expense = Expense(date = datetime.datetime.now(),
                          amount = form.cleaned_data['amount'],
                          item_name = form.cleaned_data['item_name'],
                          category = cate)
        expense.save()
        t = threading.Thread(target=play_output, args=["new entry created",])
        t.setDaemon(False)
        t.start()
        request.session['message'] = 'Entry saved'
        context['form'] = ExpenseForm()
        return render(request, 'echobudget/home.html', context)
    form = ExpenseForm()
    context = {'message': 'Action not supported', 'active': 'home', 'form': form}
    t = threading.Thread(target=play_output, args=["action not supported",])
    t.setDaemon(False)
    t.start()
    return render(request, 'echobudget/home.html', context)

def speak_entrylist_action(request):
    params = speak_action(request)
    if len(params["error"]) != 0:
        form = DateSelectionForm()
        t = threading.Thread(target=play_output, args=["i Try again",])
        t.setDaemon(False)
        t.start()
        return render(request, 'echobudget/record.html', {"message": params["error"], "active": "record", "form": form})
    page = parse_verb(request, params)
    if page:
        return page
    if "modify" in params["action"]:
        print(params["num"])
        context = {'active': 'record', 'entryid': params["num"]}
        obj = None
        try:
            obj = Expense.objects.get(id=params["num"])
        except:
            print("exception")
            request.session['message'] = "Invalid entry id"
            return redirect('entrylist')
        category = obj.category.id
        initial_data = {
            'category': category,
            'amount': float(obj.amount),
            'item_name': obj.item_name
        }
        form = ExpenseForm(initial_data)
        context['form'] = form
        initial_data['id'] = str(params['num'])
        request.session['modifying'] = initial_data
        output = "i modifying item number " + initial_data['id'] + ". Say change price to eight dollars for example to modify price, same for category and item name. Available categories are: food, housing, necessities, transportation, entertainment, and others."
        t = threading.Thread(target=play_output, args=[output,])
        t.setDaemon(False)
        t.start()
        return render(request, 'echobudget/modify.html', context)
    if "remove" in params["action"]:
        context = {'active': 'record'}
        obj = None
        try:
            obj = Expense.objects.get(id=params["num"])
        except:
            request.session['message'] = "Invalid entry id"
            return redirect('entrylist')
        obj.delete()
        t = threading.Thread(target=play_output, args=["the item removed",])
        t.setDaemon(False)
        t.start()
        return redirect('entrylist')
    form = DateSelectionForm()
    context = {'message': 'Action not supported', 'active': 'record', 'form': form}
    t = threading.Thread(target=play_output, args=["action not supported",])
    t.setDaemon(False)
    t.start()
    return render(request, 'echobudget/record.html', context)

def speak_modify_action(request):
    params = speak_action(request)
    initial_data = copy.deepcopy(request.session.get('modifying'))
    if not initial_data:
        return redirect('entrylist')
    entry_id = int(initial_data['id'])
    initial_data.pop('id')
    form = ExpenseForm(initial_data)
    if len(params["error"]) != 0:
        t = threading.Thread(target=play_output, args=[params['error'],])
        t.setDaemon(False)
        t.start()
        return render(request, 'echobudget/record.html', {"message": params["error"], "active": "record", "form": form})
    page = parse_verb(request, params)
    if page:
        return page
    if 'change' in params['action']:
        print('enter change')
        context = {'active': 'record'}
        label = params['label']
        if 'price' in label:
            p = params['price'].split(' ')[0]
            if len(p) == 0:
                p = params['num']
            initial_data['amount'] = round(float(p), 2)
            print(initial_data['amount'])
        if 'category' in label:
            category = params['category'][0].upper() + params['category'][1:]
            print("category little:", params['category'])
            print("category cap:", category)
            c = Category.objects.get(name=category)
            initial_data['category'] = c.id
        if 'item name' in label:
            initial_data['item_name'] = params['item']
        form = ExpenseForm(initial_data)
        initial_data['id'] = entry_id
        request.session['modifying'] = initial_data
        price = str(initial_data['amount'])
        category = Category.objects.get(id=initial_data['category']).name
        output = "i Entering " + initial_data['item_name'] + " for " + price + " dollars as " + category + ", please press the speaking button and confirm"
        t = threading.Thread(target=play_output, args=[output,])
        t.setDaemon(False)
        t.start()
        context['form'] = form
        context['entryid'] = entry_id
        return render(request, 'echobudget/modify.html', context)
    if 'confirm' in params['action']:
        context = {'active': 'record'}
        initial_data = request.session.get('modifying')
        del request.session['modifying']
        entry_id = initial_data['id']
        initial_data.pop('id')
        form = ExpenseForm(initial_data)
        if not form or not form.is_valid():
            print("form not valid")
            context = {'message': "Invalid Form"}
            return render(request, 'echobudget/record.html', context)
        try:
            obj = Expense.objects.get(id=entry_id)
        except:
            request.session['message'] = "Invalid entry id"
            return redirect('entrylist')
        try:
            cate = Category.objects.get(id=form.cleaned_data['category'])
        except:
            request.session['message'] = "Invalid category"
            return redirect('entrylist')
        obj.category = cate
        obj.amount = form.cleaned_data['amount']
        obj.item_name = form.cleaned_data['item_name']
        obj.save()
        add_item(obj.item_name, obj.category.name)
        t = threading.Thread(target=play_output, args=["the entry updated",])
        t.setDaemon(False)
        t.start()
        request.session['message'] = "Entry updated"
        return redirect('entrylist')
    context = {'message': 'Action not supported', 'active': 'record', 'form': form}
    t = threading.Thread(target=play_output, args=["action not supported",])
    t.setDaemon(False)
    t.start()
    return render(request, 'echobudget/modify.html', context)

def modify_action(request, id):
    context = {'active': 'record', 'entryid': id}
    if 'message' in request.session:
        # display the message and delete it in request.session
        message = request.session['message']
        context['message'] = message
        del request.session['message']
    if request.method == 'GET':
        obj = None
        try:
            obj = Expense.objects.get(id=id)
        except:
            request.session['message'] = "Invalid entry id"
            return redirect('entrylist')
        category = obj.category.id
        initial_data = {
            'category': category,
            'amount': obj.amount,
            'item_name': obj.item_name
        }
        form = ExpenseForm(initial_data)
        context['form'] = form
        return render(request, 'echobudget/modify.html', context)
    elif request.method == 'POST':
        form = ExpenseForm(request.POST)
        if not form.is_valid():
            request.session['message'] = "Invalid form"
            context = {'message': "Invalid Form"}
            return redirect('modify', id)
        try:
            obj = Expense.objects.get(id=id)
        except:
            request.session['message'] = "Invalid entry id"
            return redirect('entrylist')
        try:
            cate = Category.objects.get(id=form.cleaned_data['category'])
        except:
            request.session['message'] = "Invalid category"
            return redirect('entrylist')
        obj.category = cate
        obj.amount = form.cleaned_data['amount']
        obj.item_name = form.cleaned_data['item_name']
        obj.save()
        add_item(obj.item_name, obj.category.name)
        request.session['message'] = "Entry updated"
        return redirect('entrylist')

def delete_action(request, id):
    context = {'active': 'record'}
    if request.method == 'GET':
        obj = None
        try:
            obj = Expense.objects.get(id=id)
        except:
            request.session['message'] = "Invalid entry id"
            return redirect('entrylist')
        obj.delete()
    return redirect('entrylist')

