// Package salesinvoice implements the Sales Invoice domain logic from ERPNext.
// Migrated from: erpnext/accounts/doctype/sales_invoice/sales_invoice.py
package salesinvoice

// --- 1. Domain Structs (The Data) ---

// SalesInvoice represents the main Sales Invoice document.
// Maps to erpnext/accounts/doctype/sales_invoice/sales_invoice.json
type TaxTemplate struct {
	ID   string
	Rate float64
}

type SalesInvoice struct {
	Name                   string
	Customer               string
	Company                string
	IsPos                  bool
	IsReturn               bool
	BypassCreditLimitCheck bool
	GrandTotal             float64
	RoundedTotal           float64
	PaidAmount             float64
	WriteOffAmount         float64
	Items                  []SalesInvoiceItem
	Precision              PrecisionSettings
	UpdateStock          bool
    IsInternalCustomer   bool   // For Inter-company logic
    RepresentsCompany    string // For Inter-company logic
    InterCompanyRef     string // For Inter-company logic
    Payments             []SalesInvoicePayment // For Payment clearing logic
}

// SalesInvoiceItem represents a row in the items child table.
type SalesInvoiceItem struct {
	ItemCode     string
	Qty          float64
	SalesOrder   string // Link to Sales Order
	DeliveryNote string // Link to Delivery Note
	DeliveredBySupplier bool // Add this for drop-ship check

}

// PrecisionSettings defines the rounding precision for calculations.
type PrecisionSettings struct {
	GrandTotal int
}

// --- 2. Helper Structs for Data Transfer ---

type LoyaltyInfo struct {
	ProgramName string
	Points      int
}

type Address struct {
	ID   string
	City string
}

// --- 3. Domain Interfaces (The Ports) ---
// These define what the domain NEEDS from the outside world (DB, APIs).
//

// CustomerRegistry abstracts customer-related data access.
type CustomerRegistry interface {
    GetLoyaltyDetails(customerID string) (LoyaltyInfo, error)
    ValidateCreditLimit(customerID string, company string) error
    GetAddressDetails(addressID string) (Address, error)
	GetAllowedCompanies(customerID string) ([]string, error)
	
}

// StockProvider abstracts item and inventory validation.
type StockProvider interface {
    GetItemValuation(itemCode string, warehouse string) (float64, error)
    ValidateUOM(itemCode string, uom string) (float64, error) // Returns conversion factor
    CheckBatchSerialAvailability(itemCode string, batch string, serials []string) error
}

// FinanceLookup abstracts financial and accounting lookups.
type FinanceLookup interface {
    GetExchangeRate(fromCurrency string, toCurrency string) (float64, error)
    VerifyAccount(accountID string, company string) (bool, error)
    GetTaxTemplate(category string) (TaxTemplate, error)
}

type CreditChecker interface {
    // CheckLimit verifies against the customer/company credit records
    CheckLimit(customer string, company string, bypass bool) error
}

type SalesInvoicePayment struct {
    ModeOfPayment string
    Amount        float64
}

