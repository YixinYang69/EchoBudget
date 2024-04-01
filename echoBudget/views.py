from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404
from django.urls import reverse

from echoBudget.forms import ExpenseForm, DateSelectionForm
from echoBudget.models import Expense, Category

import datetime, json
import speech_recognition as sr

import spacy

nlp = spacy.load("en_core_web_sm")

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
    context = {'form': form, 'active': 'report', 'labels': labels, 'data': data}
    return render(request, 'echobudget/report.html', context)

def speak_action(request):
    if request.method == "POST":
        r = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                audio = r.listen(source, 10, 5)
            text_output = r.recognize_google(audio)
            print("text_output: " + text_output)
            if "report" in text_output:
                print("yes!")
            doc = nlp(text_output)
            action = ""
            for token in doc:
                if (token.pos_ == "VERB"):
                    action = token.text

                    
            # for ent in doc.ents:
            #     if (ent.label_ == "DATE"):
            #         # month year to month year
            #         date = ent.text
            #     if (ent.label_ == "MONEY"):
            #         # $5 // 5 dollars
            #         price = ent.text
            #     if (ent.label_ == "ITEM"):
            #         item = ent.text
            print(action)
            print(type(action))
            print(action == "generate")
            if "enter" in action:
                return redirect('/home')
            if "get" in action:
                return redirect('/entrylist')
            if "generate" in action:
                print("action correct!!")
                return redirect('/report')
            else:
                return render(request, 'echobudget/base.html', {'text': text_output})
        except sr.WaitTimeoutError:
            return render(request, 'echobudget/base.html', {'text': "Didn't hear"})
        except sr.UnknownValueError:
            return render(request, 'echobudget/base.html', {'text': "Ooops"})