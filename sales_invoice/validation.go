package salesinvoice

import (
	"errors"
	"fmt"
	"math"
)

// --- 1. Sentinel Errors ---
// These allow callers to handle specific business failures programmatically.

var (
	// ErrPOSAmountExceedsGrandTotal matches the logic in validate_pos.
	ErrPOSAmountExceedsGrandTotal = errors.New("paid amount + write off amount cannot be greater than grand total")

	// ErrCreditLimitExceeded matches the logic in check_credit_limit.
	ErrCreditLimitExceeded = errors.New("customer credit limit exceeded")

	// Warehouse/Stock Errors identified via legacy extraction.
	ErrDropShippingStockUpdate = errors.New("stock cannot be updated for drop shipping items")

	// Inter-company Errors identified via legacy extraction.
	ErrInvalidInterCompanyEntity = errors.New("invalid entity for inter company transaction")

	// Item Errors.
	ErrInvalidQty = errors.New("item quantity cannot be zero")
)

// --- 2. Validation Error Wrapper ---
// Wraps sentinel errors with human-readable details for better debugging.

type ValidationError struct {
	Err     error
	Details string
}

func (e *ValidationError) Error() string {
	if e.Details != "" {
		return fmt.Sprintf("%s: %s", e.Err.Error(), e.Details)
	}
	return e.Err.Error()
}

func (e *ValidationError) Unwrap() error {
	return e.Err
}

// --- 3. Business Rules (The logic we extracted) ---

// ValidatePOS checks if paid amount + write-off exceeds the total for returns.
func (s *SalesInvoice) ValidatePOS() error {
	if !s.IsReturn {
		return nil
	}

	totalPaid := s.PaidAmount + s.WriteOffAmount
	invoiceTotal := s.GrandTotal
	
	// Handles rounding edge cases found in the coverage report.
	if s.RoundedTotal > 0 {
		invoiceTotal = s.RoundedTotal
	}

	// Calculate tolerance based on precision found in Python legacy.
	tolerance := 1.0 / math.Pow(10, float64(s.Precision.GrandTotal+1))

	if (totalPaid - invoiceTotal) > tolerance {
		return &ValidationError{
			Err:     ErrPOSAmountExceedsGrandTotal,
			Details: fmt.Sprintf("total paid %.2f exceeds invoice total %.2f", totalPaid, invoiceTotal),
		}
	}
	return nil
}

// CheckCreditLimit validates the customer's credit limit via the checker port.
func (s *SalesInvoice) CheckCreditLimit(checker CreditChecker) error {
	// If bypass is true, we start with FALSE (do not validate).
	// If bypass is false, we start with TRUE (must validate).
	validateAgainstLimit := !s.BypassCreditLimitCheck

	// Forced validation if items are not linked to previous docs.
	for _, item := range s.Items {
		if item.SalesOrder == "" && item.DeliveryNote == "" {
			validateAgainstLimit = true
			break
		}
	}

	if validateAgainstLimit {
		return checker.CheckLimit(s.Customer, s.Company, s.BypassCreditLimitCheck)
	}
	return nil
}

// ValidateDropShip ensures stock updates aren't triggered for supplier-delivered items.
func (s *SalesInvoice) ValidateDropShip() error {
	if !s.UpdateStock {
		return nil
	}
	for _, item := range s.Items {
		if item.DeliveredBySupplier {
			return &ValidationError{Err: ErrDropShippingStockUpdate}
		}
	}
	return nil
}

// ValidateInterCompany checks if internal customers are authorized for the company.
func (s *SalesInvoice) ValidateInterCompany(registry CustomerRegistry) error {
	if s.InterCompanyRef == "" && s.IsInternalCustomer {
		allowed, err := registry.GetAllowedCompanies(s.Customer)
		if err != nil || !contains(allowed, s.Company) {
			return &ValidationError{Err: ErrInvalidInterCompanyEntity}
		}
	}
	return nil
}

// --- 4. Orchestrator (The Pipeline) ---
// This matches the validate() method in ERPNext that calls all sub-validations.

func (s *SalesInvoice) Validate(creditChecker CreditChecker, registry CustomerRegistry) error {
	if err := s.ValidatePOS(); err != nil {
		return err
	}
	if err := s.CheckCreditLimit(creditChecker); err != nil {
		return err
	}
	if err := s.ValidateDropShip(); err != nil {
		return err
	}
	if err := s.ValidateInterCompany(registry); err != nil {
		return err
	}
	return nil
}

// --- 5. Helpers ---

// contains resolves the "undefined: contains" compiler error.
func contains(slice []string, item string) bool {
	for _, s := range slice {
		if s == item {
			return true
		}
	}
	return false
}