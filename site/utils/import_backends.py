#!/usr/bin/python
# -*- coding: utf-8 -*-
import csv
import logging
import datetime

from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.db import DataError

from project.generators import (DEFAULT_TEST_DATA, CompanyShareholderGenerator,
                                OperatorGenerator)
from shareholder.models import (Company, Position, Security,
                                Shareholder, OptionPlan, OptionTransaction)

SISWARE_CSV_HEADER = [
    'Aktion\x8arID', 'Aktion\x8arsArt', 'Eintragungsart', 'Suchname',
    'Firmaname', 'FirmaAbteilung', 'Titel', 'Anrede', 'Vorname',
    'Vorname Zusatz', 'Name', 'Adresse', 'Adresse2', 'Postfach', 'Nr Postfach',
    'PLZ', 'Ort', 'Land', 'C/O', 'Geburtsdatum', 'Sprache', 'VersandArt',
    'Nationalit\x8at', 'AktienArt', 'Valoren-Nr', 'Nennwert', 'Anzahl Aktien',
    'Zertifikat-Nr', 'Ausgestellt am', 'Skontro-Nr', 'DepotArt'
]

logger = logging.getLogger(__name__)


class BaseImportBackend(object):
    """
    common logic to import captable data from a source into a companies account
    """

    def __init__(self, filename):

        self.filename = filename
        self.validate(filename)

    def validate(self, filename):
        """
        is this a good file for this backend?
        """
        raise NotImplementedError('create me!')

    def import_from_file(self, filename, company_pk):
        """
        read file contents and place them into the database
        """
        raise NotImplementedError('create me!')


class SisWareImportBackend(BaseImportBackend):
    """
    import from sisware share register in switzerland

    import does not import history, it creates an initial transaction and
    assumes that the share register starts with the import
    """

    def _init_import(self, company_pk):
        """
        check and/or prepare data required for the import

        security not treated here, will be created upon existence while parsing
        the rows
        """
        # do we have a company?
        try:
            self.company = Company.objects.get(pk=company_pk)
        except Company.DoesNotExist:
            raise ValueError('company not existing. please create company and '
                             'operator first')

        # with a company shareholder?
        try:
            self.company_shareholder = self.company.get_company_shareholder()
        except ValueError:
            self.company_shareholder = CompanyShareholderGenerator().generate(
                company=self.company)

        # and a matching operator?
        self.operator = self.company.operator_set.first()
        if not self.operator:
            logger.info('operator created')
            self.operator = OperatorGenerator().generate(
                company=self.company)
            print u'operator created with username {} and pw {}'.format(
                self.operator.user.username, DEFAULT_TEST_DATA.get('password'))

    def _import_row(self, row):
        """
        import a single line of the data set
        """
        if not [field for field in row if field != u'']:
            return 0

        user = self._get_or_create_user(row[0], row[8]+' '+row[9], row[10])
        shareholder = self._get_or_create_shareholder(row[0], user)
        # plan shares
        if not row[27]:
            self._get_or_create_position(
                bought_at=row[28], buyer=shareholder, count=row[26],
                value=row[25],
                face_value=float(row[25].replace(',', '.')))
        # options
        else:
            self._get_or_create_option_transaction(
                cert_id=row[27], bought_at=row[28], buyer=shareholder,
                count=row[26], face_value=float(row[25].replace(',', '.')))

        return 1

    def _finish_import(self):
        """
        check data consistency, company data, total sums to ensure the import is
        fully valid
        """
        # FIXME update security.count
        logger.warning('import finishing not implemented')

    def _get_or_create_shareholder(self, shareholder_number, user):
        shareholder, c_ = Shareholder.objects.get_or_create(
            number=shareholder_number, company=self.company,
            defaults={'company': self.company,
                      'number': shareholder_number,
                      'user': user
                      }
        )
        return shareholder

    def _get_or_create_security(self, face_value):

        security, c_ = Security.objects.get_or_create(
            title='R', face_value=face_value,
            company=self.company, count=1)  # count=1 intermediary

        return security

    def _get_or_create_position(self, bought_at, buyer, count, value,
                                face_value, **kwargs):
        """
        we have no history data, hence, we start with an initial position/
        transaction of the day of the import
        """
        seller = self.company.get_company_shareholder()
        security = self._get_or_create_security(face_value)

        # FIXME add scontro and depot type to lookup
        position, c_ = Position.objects.get_or_create(
            bought_at=bought_at[0:10], seller=seller, buyer=buyer,
            security=security, count=int(count),
            defaults={
                'value': float(value.replace(',', '.')),
            })

        if not c_:
            print (u'position for {} "{} {}"->"{} {}" {} with pk {} existing'
                   u''.format(
                    bought_at, seller.user.first_name, seller.user.last_name,
                    buyer.user.first_name, buyer.user.last_name, security,
                    position.pk))

        return position

    def _get_or_create_option_transaction(self, cert_id, bought_at, buyer,
                                          count, face_value):

        security = self._get_or_create_security(face_value)
        option_plan, c_ = OptionPlan.objects.get_or_create(
            company=self.company, security=security,
            defaults={
                'title': _('Default OptionPlan for {}').format(security),
                'count': 0,
                'exercise_price': 1,
                'board_approved_at': datetime.datetime(2013, 1, 1),
            })
        seller = self.company.get_company_shareholder()

        option, c_ = OptionTransaction.objects.get_or_create(
            certificate_id=cert_id, bought_at=bought_at[0:10], buyer=buyer,
            seller=seller, count=count, option_plan=option_plan)

        return option

    def _get_or_create_user(self, shareholder_id, first_name, last_name):
        """
        we have no email to identify duplicates and merge then. hence we are
        using the shareholder id to create new users for each shareholder id
        """
        username = u"{}-{}".format(slugify(self.company.name), shareholder_id)
        try:
            user, c_ = User.objects.get_or_create(
                username=username[:29],
                defaults={u'first_name': first_name, u'last_name': last_name}
            )
        except DataError as e:
            # some users might have last name exceeding max length.
            print (u'create user failed for {} {}. please fix data & reimport.'
                   u'hint: check string length'.format(first_name, last_name))
            raise e

        return user

    def validate(self, filename):
        """
        validate if file can be used
        """
        with open(filename) as f:
            reader = csv.reader(f, delimiter=';')
            for row in reader:
                if row == SISWARE_CSV_HEADER:
                    break
                else:
                    raise ValueError('invalid file for sisware import backend')

    def import_from_file(self, company_pk):
        """
        read file contents and place them into the database
        """

        self._init_import(company_pk)

        with open(self.filename) as f:
            reader = csv.reader(f, delimiter=';')
            self.row_count = 0
            for row in reader:
                if row == SISWARE_CSV_HEADER:
                    continue
                self.row_count += self._import_row(
                    [value.strip().decode('ISO-8859-1') for value in row])

        self._finish_import()

        return self.row_count

# reusable  list of available import backends
IMPORT_BACKENDS = [
    SisWareImportBackend,
]
