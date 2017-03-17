# -*- coding: utf-8 -*-
# Generated by Django 1.9.8 on 2017-02-11 23:03
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shareholder', '0059_auto_20170202_2143'),
    ]

    operations = [
        migrations.AddField(
            model_name='optiontransaction',
            name='is_printed',
            field=models.BooleanField(default=False, verbose_name='was this printed at least once?'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='initial_registration_at',
            field=models.DateField(blank=True, null=True, verbose_name='Datum der Ersteintragung ins Register'),
        ),
    ]
