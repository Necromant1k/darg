# -*- coding: utf-8 -*-
# Generated by Django 1.9.8 on 2017-02-12 11:58
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shareholder', '0062_company_pdf_header_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='signatures',
            field=models.CharField(blank=True, max_length=255, verbose_name='comma separated list of board members permitted to sign in the name of the company'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='url',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='optiontransaction',
            name='printed_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Datum des ersten Drucks'),
        ),
    ]