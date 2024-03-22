from django import forms
from django.db import models

from echoBudget.models import Category, Expense

class ExpenseForm(forms.Form):
    category = forms.ChoiceField(widget=forms.Select(attrs={'class': 'choice_form', 'placeholder': 'Select from below'}))
    amount = forms.DecimalField(label="Cost", max_digits=12, widget=forms.NumberInput(attrs={'class': 'amount_form', 'placeholder': 'Required'}), min_value=0, decimal_places=2)
    # date = forms.DateField(widget=forms.NumberInput(attrs={'type': 'date'}))
    item_name = forms.CharField(widget=forms.TextInput(attrs={'class':'text_form', 'placeholder': 'Required'}), max_length=30)

    def __init__(self, *args):
        super().__init__(*args)
        cat_choices = []
        for item in Category.objects.all():
            cat_choices.append((item.id, item.name))
        self.fields['category'].choices = cat_choices
    
    def clean(self):
        cleaned_data = super().clean()
        item_name = cleaned_data['item_name']
        if not all(x.isalnum() or x.isspace() for x in item_name):
            raise forms.ValidationError("Item name can only contain numbers, letters, and spaces.")
        return cleaned_data

class DateSelectionForm(forms.Form):
    start_date = forms.DateField(widget=forms.NumberInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.NumberInput(attrs={'type': 'date'}))

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date > end_date:
            raise forms.ValidationError("Start date must be before end date.")
        return cleaned_data