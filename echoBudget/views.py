from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404
from django.urls import reverse

from echoBudget.forms import ExpenseForm, DateSelectionForm
from echoBudget.models import Expense, Category

import datetime, json

# Create your views here.
def home_action(request):
    context = {}
    if 'message' in request.session:
        # display the message and delete it in request.session
        message = request.session['message']
        context['message'] = message
        del request.session['message']
    if request.method == "GET":
        form = ExpenseForm()
        context['form'] = form
    return render(request, 'echobudget/home.html', context)

def list_action(request):
    if request.method == "GET":
        form = DateSelectionForm()
        context = {'form': form}
        return render(request, 'echoBudget/record.html', context)

def report_action(request):
    if request.method == "GET":
        form = DateSelectionForm()
        context = {'form': form}
        return render(request, 'echoBudget/record.html', context)

def create_entry(request):
    pass
