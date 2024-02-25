from django import forms
from django.db import models

class ExpenseForm(forms.Form):
    category = forms.ChoiceField(widget=forms.Select(attrs={'class': 'choice_form', 'placeholder': 'Select from below'}))
    amount = forms.DecimalField(label="Cost", widget=forms.NumberInput(attrs={'class': 'amount_form', 'placeholder': 'Required'}), min_value=0, decimal_places=2)
    date = forms.DateField(widget=forms.NumberInput(attrs={'type': 'date'}))
    item_name = forms.CharField(widget=forms.TextInput(attrs={'class':'text_form', 'placeholder': 'Required'}), max_length=30)

    def __init__(self, *args, account):
        super().__init__(*args)
        cat_choices = []
        for item in Category.objects.all():
            cat_choices.append(item.name)
        self.fields['category'].choices = tuple(cat_choices)
    
    def clean(self):
        cleaned_data = super().clean()
