from django.db import models

# Create your models here.

class Expense(models.Model):
    date = models.DateField()
    amount = models.DecimalField(decimal_places=2)
    item_name = models.CharField(max_length=30)
    category = models.ForeignKey(Category, default=None, related_name="expenses")

class Category(models.Model):
    name = models.CharField(max_length=30)
    color = models.CharField(max_length=7, default="#000000")
