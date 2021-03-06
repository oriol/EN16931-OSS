"""
Class for representing an Invoice.
"""
from datetime import datetime
import lxml.etree

from money.currency import Currency

from en16931.entity import Entity
from en16931.money import MyMoney
from en16931.utils import parse_date
from en16931.utils import parse_money
from en16931.xpaths import get_from_xpath
from en16931.xpaths import get_entity
from en16931.xpaths import get_invoice_lines
from en16931.xpaths import get_discount
from en16931.xpaths import get_charge

from jinja2 import Environment, PackageLoader

templates = Environment(loader=PackageLoader('en16931', 'templates'))


class Invoice:

    def __init__(self, invoice_id=None, currency="EUR", from_xml=False):
        """Initialize an Invoice.

        This is the main class and entry point for creating an Invoice.


        Parameters
        ----------
        invoice_id: string (optional, default '1')
            Arbitrary string to identify the invoice.

        currency: string (optional, default 'EUR')
            An ISO 4217 currency code.

        from_xml: bool (optional, default False)
            A flag to mark if the object is the result of importing
            an XML invoice.


        Raises
        ------
        KeyError: If the currency code is not a valid ISO 4217 code.


        Examples
        --------

        By default the currency of the invoice is EUR and its id is 1:

        >>> i = Invoice()
        >>> i.invoice_id
        1
        >>> i.currency
        EUR

        You can also specify an arbitrary id and a valid ISO 4217
        currency code.

        >>> i = Invoice(invoice_id="0001-2018", currency="USD")
        >>> i.invoice_id
        0001-2018
        >>> i.currency
        USD

        """
        self.invoice_id = invoice_id or '1'
        self.currency = currency
        self.ubl_version_id = "2.1"
        self.customization_id = "urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0"
        self.profile_id = "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"
        self.invoice_type_code = 380
        self._issue_date = None
        self._due_date = None
        self._seller_party = None
        self._buyer_party = None
        self._templates = templates.get_template('invoice.xml')
        self._imported_from_xml = from_xml
        self._line_extension_amount = None
        self._tax_exclusive_amount = None
        self._tax_inclusive_amount = None
        self._payable_amount = None
        self._charge_amount = None
        self._charge_percent = None
        self._discount_amount = None
        self._discount_percent = None
        self.lines = []

    @classmethod
    def from_xml(cls, xml_path):
        """Import a XML invoice in EN16931 format.


        Parameters
        ----------
        xml_path: path
            A path to the XML file.


        Raises
        ------
        FileNotFoundError: if the file does not exist.


        Examples
        --------

        >>> i = Invoice.from_xml('path/to/invoice.xml')

        """
        with open(xml_path, "rb") as f:
            xml = f.read()
        root = lxml.etree.fromstring(xml)
        invoice_id = get_from_xpath(root, "invoice_id")
        currency = get_from_xpath(root, "currency")
        invoice = cls(invoice_id=invoice_id, currency=currency, from_xml=True)
        invoice.issue_date = get_from_xpath(root, "invoice_issue_date")
        invoice.due_date = get_from_xpath(root, "invoice_due_date")
        # seller and buyer
        invoice.seller_party = get_entity(root, kind='seller')
        invoice.buyer_party = get_entity(root, kind='buyer')
        # totals
        invoice.line_extension_amount = get_from_xpath(root, "invoice_line_extension_amount")
        invoice.tax_exclusive_amount = get_from_xpath(root, "tax_exclusive_amount")
        invoice.tax_inclusive_amount = get_from_xpath(root, "tax_inclusive_amount")
        invoice.payable_amount = get_from_xpath(root, "payable_amount")
        # lines
        invoice.add_lines_from(get_invoice_lines(root))
        # discount and charge
        discount = get_discount(root)
        if discount is not None:
            invoice.discount = discount
        charge = get_charge(root)
        if charge is not None:
            invoice.charge = charge
        return invoice

    @property
    def currency(self):
        """String representation of the ISO 4217 currency code.
        """
        return self._currency.name

    @currency.setter
    def currency(self, currency_str):
        """Sets the currency of the Invoice.


        Parameters
        ----------
        currency_str: string
            String representation of the ISO 4217 currency code.


        Raises
        ------
        KeyError: If the currency code is not a valid ISO 4217 code.

        """
        try:
            self._currency = Currency[currency_str]
        except KeyError:
            raise KeyError('Currency {} not suported'.format(currency_str))

    def to_xml(self):
        """Serialize the invoice object to XML.

        Generate a valid PEPPOL BIS 3 XML document using the UBL 2.1
        syntax.
        """
        return self._templates.render(invoice=self)

    def save(self, path=None):
        """Save the XML representation of the invoice.


        Parameters
        ----------
        path: a path (optional, default None)
            If the path is None it a file named 'invoice_id.xml'
            will be created in the current working directory.

        """
        if path is None:
            path = 'invoice_{}.xml'.format(self.invoice_id)
        with open(path, 'w') as f:
            f.write(self.to_xml())

    @property
    def issue_date(self):
        """The issue date of the invoice.
        """
        return self._issue_date

    @issue_date.setter
    def issue_date(self, date):
        """Set the issue date of the invoice.


        Parameters
        ----------
        date: datetime or string
            If the input is a string, it should be in one of the
            following formats: "%Y-%m-%d", "%Y%m%d", "%d-%m-%Y",
            "%Y/%m/%d", "%d/%m/%Y".


        Raises
        ------
        ValueError: if the input string cannot be converted to a
            datetime object.

        
        Examples
        --------

        >>> from datetime import datetime
        >>> i = Invoice()
    
        Supported date formats are:

        >>> i.issue_date = datetime(2018, 6, 21)
        >>> i.issue_date
        datetime.datetime(2018, 6, 21, 0, 0)
        >>> i.issue_date = "2018-06-21"
        datetime.datetime(2018, 6, 21, 0, 0)
        >>> i.issue_date = "20180621"
        datetime.datetime(2018, 6, 21, 0, 0)
        >>> i.issue_date = "21-6-2018"
        datetime.datetime(2018, 6, 21, 0, 0)
        >>> i.issue_date = "2018/06/21"
        datetime.datetime(2018, 6, 21, 0, 0)
        >>> i.issue_date = "21/6/2018"
        datetime.datetime(2018, 6, 21, 0, 0)

        Incorrect date formats will raise a ValueError:

        >>> i.issue_date = "today"
        Traceback (most recent call last):
        [...]
        ValueError: See documentation for string date formats supported

        """
        if not date:
            return
        elif isinstance(date, datetime):
            self._issue_date = date
        elif isinstance(date, str):
            self._issue_date = parse_date(date)
        else:
            raise ValueError("Unrecognized date")

    @property
    def due_date(self):
        """Due date of the invoice.
        """
        return self._due_date

    @due_date.setter
    def due_date(self, date):
        """Set the due date of the invoice.


        Parameters
        ----------
        date: datetime or string
            If the input is a string, it should be in one of the
            following formats: "%Y-%m-%d", "%Y%m%d", "%d-%m-%Y",
            "%Y/%m/%d", "%d/%m/%Y".


        Raises
        ------
        ValueError: if the input string cannot be converted to a
            datetime object.

        
        Examples
        --------

        >>> from datetime import datetime
        >>> i = Invoice()
    
        Supported date formats are:

        >>> i.due_date = datetime(2018, 6, 21)
        >>> i.due_date
        datetime.datetime(2018, 6, 21, 0, 0)
        >>> i.due_date = "2018-06-21"
        datetime.datetime(2018, 6, 21, 0, 0)
        >>> i.due_date = "20180621"
        datetime.datetime(2018, 6, 21, 0, 0)
        >>> i.due_date = "21-6-2018"
        datetime.datetime(2018, 6, 21, 0, 0)
        >>> i.due_date = "2018/06/21"
        datetime.datetime(2018, 6, 21, 0, 0)
        >>> i.due_date = "21/6/2018"
        datetime.datetime(2018, 6, 21, 0, 0)

        Incorrect date formats will raise a ValueError:

        >>> i.due_date = "today"
        Traceback (most recent call last):
        [...]
        ValueError: See documentation for string date formats supported

        """

        if not date:
            return
        elif isinstance(date, datetime):
            self._due_date = date
        elif isinstance(date, str):
            self._due_date = parse_date(date)
        else:
            raise ValueError("Unrecognized date")

    @property
    def seller_party(self):
        """The Entity with the role of AccountingSupplierParty.

        See the Entity class for details
        """
        return self._seller_party

    @seller_party.setter
    def seller_party(self, party):
        """Set the Entity with the role of AccountingSupplierParty.

        Parameters
        ----------
        party: Entity object.
            The Entity object that plays the role of
            AccountingSupplierParty.

        Raises
        ------
        ValueError: if the Entity is not valid.

        TypeError: if the input is not an Entity or Entity subclass.

        """
        if isinstance(party, Entity):
            if party.is_valid():
                self._seller_party = party
            else:
                raise ValueError("Invalid Entity")
        else:
            msg = "Expected an Entity object but got a {}"
            raise TypeError(msg.format(type(party)))

    @property
    def buyer_party(self):
        """The Entity with the role of AccountingCustomerParty.

        See the Entity class for details
        """
        return self._buyer_party

    @buyer_party.setter
    def buyer_party(self, party):
        """Set the Entity with the role of AccountingCustomerParty.

        Parameters
        ----------
        party: Entity object.
            The Entity object that plays the role of
            AccountingCustomerParty.

        Raises
        ------
        ValueError: if the Entity is not valid.

        TypeError: if the input is not an Entity or Entity subclass.

        """
        if isinstance(party, Entity):
            if party.is_valid():
                self._buyer_party = party
            else:
                raise ValueError("Invalid Entity")
        else:
            msg = "Expected an Entity object but got a {}"
            raise TypeError(msg.format(type(party)))

    @property
    def charge(self):
        """The ChargeTotalAmount of the Invoice.
        """
        if self._charge_amount is not None:
            return self._charge_amount
        else:
            return MyMoney('0', self._currency)

    @charge.setter
    def charge(self, value):
        """Sets the ChargeTotalAmount of the invoice.

        Parameters
        ----------
        value: string, integer, float
            The input must be a valid input for the Decimal class
            the Python Standard Library.

        Raises
        ------
        decimal.InvalidOperation: If the input cannot be converted
            to a Decimal.

        """
        self._charge_amount = parse_money(value, self._currency)
        self._charge_percent = round(self._charge_amount / self.gross_subtotal(), 2)

    @property
    def charge_percent(self):
        """The percentage that the charge represents.

        The MultiplierFactorNumeric of the charge in PEPPOL BIS 3 terms.
        """
        return self._charge_percent

    @property
    def charge_base_amount(self):
        """The base amount of the charge.

        The BaseAmount of the charge in PEPPOL BIS 3 terms.
        """
        if self._charge_amount is not None and self._charge_percent is not None:
            return self._charge_amount / self._charge_percent

    @property
    def discount(self):
        """The AllowanceTotalAmount of the Invoice.
        """
        if self._discount_amount is not None:
            return self._discount_amount
        else:
            return MyMoney('0', self._currency)

    @discount.setter
    def discount(self, value):
        """Sets the AllowanceTotalAmount of the invoice.

        Parameters
        ----------
        value: string, integer, float
            The input must be a valid input for the Decimal class
            the Python Standard Library.

        Raises
        ------
        decimal.InvalidOperation: If the input cannot be converted
            to a Decimal.

        """
        self._discount_amount = parse_money(value, self._currency)
        self._discount_percent = round(self._discount_amount / self.gross_subtotal(), 2)

    @property
    def discount_percent(self):
        """The percentage that the discount represents.

        The MultiplierFactorNumeric of the discount in PEPPOL BIS 3 terms.
        """
        return self._discount_percent

    @property
    def discount_base_amount(self):
        """The base amount of the discount.

        The BaseAmount of the discount in PEPPOL BIS 3 terms.
        """
        if self._discount_amount is not None and self._discount_percent is not None:
            return self._discount_amount / self._discount_percent

    def add_line(self, line):
        """Adds an InvoiceLine to the Invoice.

        Parameters
        ----------
        line: InvoiceLine object.

        """
        self.lines.append(line)

    def add_lines_from(self, container):
        """Adds InvoiceLine instances from a container.

        Parameters
        ----------
        container: container
            An iterable container of InvoiceLine objects.

        """
        self.lines.extend(container)

    @property
    def unique_taxes(self):
        """Set of unique taxes in the Invoice.
        """
        return {line.tax for line in self.lines}

    def lines_with_taxes(self, tax_type=None):
        """Generator of InvoiceLines

        Parameters
        ----------
        tax_type: Tax object (default None).
            If a Tax object is provided, only generate lines with that
            Tax. If this parameter is None, generate all lines.
        """
        for line in self.lines:
            if line.has_tax(tax_type):
                yield line

    def tax_amount(self, tax_type=None):
        """Computes the tax amount of the Invoice.

        Parameters
        ----------
        tax_type: Tax object (default None).
            If a Tax object is provided, the tax amount corresponding
            to the porvided Tax. If None the total tax amount.

        """
        if tax_type is None:
            taxes = self.unique_taxes
        else:
            taxes = {tax_type}
        result = (self.taxable_base(tax_type=tax) * tax.percent for tax in taxes)
        return sum(result, MyMoney('0', self._currency))

    def taxable_base(self, tax_type=None):
        """Computes the taxable base of the Invoice

        Parameters
        ----------
        tax_type: Tax object (default None).
            If a Tax object is provided, the taxable base corresponding
            to the porvided Tax. If None the total taxable base.

        """
        return self.gross_subtotal(tax_type=tax_type) - self.discount + self.charge

    def gross_subtotal(self, tax_type=None):
        """Sum of gross amount of each invoice line."""
        amounts = (line.line_extension_amount for line in
                   self.lines_with_taxes(tax_type=tax_type))
        return sum(amounts, MyMoney('0', self._currency))

    def subtotal(self, tax_type=None):
        """Gross amount before taxes.

            TotalGrossAmount - AllowanceTotalAmount + ChargeTotalAmount
        """
        gross_subtotal = self.gross_subtotal(tax_type=tax_type)
        return gross_subtotal - self.discount + self.charge

    def total(self):
        """Computes the TaxInclusiveAmount of the Invoice
        """
        return self.subtotal() + self.tax_amount()

    # Properties so we can return what was in the XML instead of computing it
    # in case we read the invoice.
    @property
    def line_extension_amount(self):
        """The total LineExtensionAmount of the invoice.

        It's only computed as the :meth:`gross_subtotal` if the Invoice
        was not imported from an XML file. In that case, its value is
        the one reported on the XML.
        """
        if self._line_extension_amount is not None:
            return self._line_extension_amount
        return self.gross_subtotal()

    @line_extension_amount.setter
    def line_extension_amount(self, value):
        """Sets the LineExtensionAmount of the invoice.

        Only used when importing from an XML file.
        """
        self._line_extension_amount = parse_money(value, self._currency)

    @property
    def tax_exclusive_amount(self):
        """The total TaxExclusiveAmount of the invoice.

        It's only computed as the :meth:`gross_subtotal` if the Invoice
        was not imported from an XML file. In that case, its value is
        the one reported on the XML.
        """
        if self._tax_exclusive_amount is not None:
            return self._tax_exclusive_amount
        return self.subtotal()

    @tax_exclusive_amount.setter
    def tax_exclusive_amount(self, value):
        """Sets the TaxExclusiveAmount of the invoice.

        Only used when importing from an XML file.
        """
        self._tax_exclusive_amount = parse_money(value, self._currency)

    @property
    def tax_inclusive_amount(self):
        """The total TaxInclusiveAmount of the invoice.

        It's only computed as the :meth:`total` if the Invoice
        was not imported from an XML file. In that case, its value is
        the one reported on the XML.
        """
        if self._tax_inclusive_amount is not None:
            return self._tax_inclusive_amount
        return self.total()

    @tax_inclusive_amount.setter
    def tax_inclusive_amount(self, value):
        """Sets the TaxInclusiveAmount of the invoice.

        Only used when importing from an XML file.
        """
        self._tax_inclusive_amount = parse_money(value, self._currency)

    @property
    def payable_amount(self):
        """The total PayableAmount of the invoice.

        It's only computed as the :meth:`total` if the Invoice
        was not imported from an XML file. In that case, its value is
        the one reported on the XML.
        """
        if self._payable_amount is not None:
            return self._payable_amount
        # TODO PrepaidAmount
        prepaid_amount = MyMoney('0', self._currency)
        return self.total() - prepaid_amount

    @payable_amount.setter
    def payable_amount(self, value):
        """Sets the PayableAmount of the invoice.

        Only used when importing from an XML file.
        """
        self._payable_amount = parse_money(value, self._currency)
