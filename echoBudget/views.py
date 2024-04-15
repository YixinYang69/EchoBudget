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
import os

nlp_default = spacy.load("en_core_web_sm")
nlp_customized = spacy.load("./model-best")

module_dir = os.path.dirname(__file__)
file_path = os.path.join(module_dir, 'sample.txt')

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
        context['form'] = form
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
        form = DateSelectionForm()
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
    if request.method == "GET":
        form = DateSelectionForm()
        today = datetime.datetime.now()
        # get first and last dates of this month
        start_date = datetime.datetime(today.year, today.month, 1)
        first_day_next_month = datetime.datetime(today.year + today.month // 12, 
            today.month % 12 + 1, 1)
        end_date = first_day_next_month - datetime.timedelta(days=1)
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
    if len(date) == 0: 
        today = datetime.datetime.now()
        # get first and last dates of this month
        start_date = datetime.datetime(today.year, today.month, 1)
        first_day_next_month = datetime.datetime(today.year + today.month // 12, 
            today.month % 12 + 1, 1)
        end_date = first_day_next_month - datetime.timedelta(days=1)
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
    entries = entry_filter(start_date, end_date)
    form = DateSelectionForm()
    context = {}
    if page == "report":
        categories = Category.objects.values_list('name', flat=True)
        labels = [c for c in categories]
        data = get_report_data(labels, entries)
        context = {'form': form, 'active': 'report', 'labels': labels, 'data': data}
    if page == "record":
        context = {'form': form, 'entries': entries, 'active': 'record'}
    return context

def play_output():
    with open(file_path, 'r') as f:
        text = f.read()
        language="en"
        tts = gTTS(text=text, lang=language)
    tts.save("output.mp3")
    os.system("afplay output.mp3")
    os.remove('output.mp3')

def speak_action(request):
    if request.method == "POST":
        r = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                play_output()
                time.sleep(1)
                audio = r.listen(source, 12, 5)
            text_output = r.recognize_google(audio)
            doc1 = nlp_default(text_output)
            doc2 = nlp_customized(text_output)

            action = ""
            date = ""
            price = ""
            num = ""
            item = ""
            action_2 = ""
            for token in doc1:
                if (token.pos_ == "VERB"):
                    action = token.text
            for ent in doc1.ents:
                if (ent.label_ == "DATE"): 
                    date = ent.text # month year to month year
                if (ent.label_ == "MONEY"): # $5 // 5 dollars
                    price = ent.text # 5 // 5 dollars
                if (ent.label_ == "CARDINAL"): # number one // No.1
                    num = ent.text # one // 1

            for ent in doc2.ents:
                if (ent.label_ == "ACTION"): # view entries // remove/modify entry // generate report // confirm
                    action_2 = ent.text
                if (ent.label_ == "ITEM"):
                    item = ent.text

            if ("enter" in action) or ("buy" in action) or ("spend" in action):
                # add items here
                return redirect('/home')
            if ("get" in action) or ("view entries" in action_2):
                context = audio_report_helper('record', date)
                return render(request, 'echobudget/record.html', context)
            if "generate" in action:
                context = audio_report_helper('report', date)
                return render(request, 'echobudget/report.html', context)
            else:
                return render(request, 'echobudget/base.html', {'text': text_output})
        except sr.WaitTimeoutError:
            return render(request, 'echobudget/base.html', {'text': "wait timeout error"})
        except sr.UnknownValueError:
            return render(request, 'echobudget/base.html', {'text': "Ooops"})

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
        request.session['message'] = "Entry updated"
        return redirect('entrylist')
