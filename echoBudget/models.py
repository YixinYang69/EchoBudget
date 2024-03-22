from django.db import models

# Create your models here.

class Category(models.Model):
    name = models.CharField(max_length=30)
    color = models.CharField(max_length=7, default="#000000")

    def __str__(self):
        return str(self.name)

class Expense(models.Model):
    date = models.DateField()
    amount = models.DecimalField(decimal_places=2, max_digits=12)
    item_name = models.CharField(max_length=30)
    category = models.ForeignKey(Category, default=None, related_name="expenses", on_delete=models.PROTECT)

