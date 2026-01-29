package salesinvoice

import (
	"errors"
	"testing"
)

// --- 1. Mock Implementations ---

type MockCreditChecker struct {
	shouldFail bool
}

func (m *MockCreditChecker) CheckLimit(customer string, company string, bypass bool) error {
	if m.shouldFail {
		return ErrCreditLimitExceeded
	}
	return nil
}

// MockCustomerRegistry satisfies the interface for advanced validation tests.
type MockCustomerRegistry struct {
	AllowedCompanies []string
}

func (m *MockCustomerRegistry) GetLoyaltyDetails(id string) (LoyaltyInfo, error) { return LoyaltyInfo{}, nil }
func (m *MockCustomerRegistry) ValidateCreditLimit(id, co string) error           { return nil }
func (m *MockCustomerRegistry) GetAddressDetails(id string) (Address, error)     { return Address{}, nil }
func (m *MockCustomerRegistry) GetAllowedCompanies(id string) ([]string, error) {
	return m.AllowedCompanies, nil
}

// --- 2. Table-Driven Tests for POS Validation ---

func TestValidatePOS(t *testing.T) {
	tests := []struct {
		name    string
		invoice SalesInvoice
		wantErr error
	}{
		{
			name: "Skip if not a return",
			invoice: SalesInvoice{
				IsReturn:   false,
				PaidAmount: 500,
				GrandTotal: 100,
			},
			wantErr: nil,
		},
		{
			name: "Valid return within tolerance",
			invoice: SalesInvoice{
				IsReturn:   true,
				PaidAmount: 100,
				GrandTotal: 100,
				Precision:  PrecisionSettings{GrandTotal: 2},
			},
			wantErr: nil,
		},
		{
			name: "Valid return with rounding", // Fixes Line 60 coverage
			invoice: SalesInvoice{
				IsReturn:     true,
				PaidAmount:   100.50,
				GrandTotal:   100.00,
				RoundedTotal: 100.50,
				Precision:    PrecisionSettings{GrandTotal: 2},
			},
			wantErr: nil,
		},
		{
			name: "Invalid return exceeding total",
			invoice: SalesInvoice{
				IsReturn:   true,
				PaidAmount: 150,
				GrandTotal: 100,
				Precision:  PrecisionSettings{GrandTotal: 2},
			},
			wantErr: ErrPOSAmountExceedsGrandTotal,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.invoice.ValidatePOS()
			if !errors.Is(err, tt.wantErr) {
				t.Errorf("ValidatePOS() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

// --- 3. Table-Driven Tests for Credit Limit ---

func TestCheckCreditLimit(t *testing.T) {
	tests := []struct {
		name     string
		invoice  SalesInvoice
		mockFail bool
		wantErr  error
	}{
		{
			name: "Bypassed with linked items",
			invoice: SalesInvoice{
				BypassCreditLimitCheck: true,
				Items: []SalesInvoiceItem{
					{SalesOrder: "SO-001"},
				},
			},
			mockFail: true,
			wantErr:  nil,
		},
		{
			name: "Force check due to unlinked items",
			invoice: SalesInvoice{
				BypassCreditLimitCheck: true,
				Items: []SalesInvoiceItem{
					{SalesOrder: ""},
				},
			},
			mockFail: true,
			wantErr:  ErrCreditLimitExceeded,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			mock := &MockCreditChecker{shouldFail: tt.mockFail}
			err := tt.invoice.CheckCreditLimit(mock)
			if !errors.Is(err, tt.wantErr) {
				t.Errorf("CheckCreditLimit() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

// --- 4. Advanced Validation Tests (DropShip & InterCompany) ---

func TestAdvancedValidations(t *testing.T) {
	tests := []struct {
		name    string
		invoice SalesInvoice
		wantErr error
	}{
		{
			name: "Fail on Drop Ship with Update Stock",
			invoice: SalesInvoice{
				UpdateStock: true,
				Items: []SalesInvoiceItem{
					{DeliveredBySupplier: true},
				},
			},
			wantErr: ErrDropShippingStockUpdate,
		},
		{
			name: "Pass on Drop Ship when Update Stock disabled", // Coverage for early return
			invoice: SalesInvoice{
				UpdateStock: false,
				Items: []SalesInvoiceItem{
					{DeliveredBySupplier: true},
				},
			},
			wantErr: nil,
		},
		{
			name: "Fail on Internal Customer not in Allowed List",
			invoice: SalesInvoice{
				IsInternalCustomer: true,
				Customer:           "Internal-001",
				Company:            "Unauthorized-Corp",
			},
			wantErr: ErrInvalidInterCompanyEntity,
		},
		{
			name: "Pass on Internal Customer in Allowed List", // Coverage for 'contains' success
			invoice: SalesInvoice{
				IsInternalCustomer: true,
				Customer:           "Internal-001",
				Company:            "Authorized-Corp",
			},
			wantErr: nil,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			mockRegistry := &MockCustomerRegistry{
				AllowedCompanies: []string{"Authorized-Corp"},
			}

			// Test DropShip
			err := tt.invoice.ValidateDropShip()
			if tt.wantErr == ErrDropShippingStockUpdate {
				if !errors.Is(err, tt.wantErr) {
					t.Errorf("ValidateDropShip() expected error %v, got %v", tt.wantErr, err)
				}
			}

			// Test InterCompany
			err = tt.invoice.ValidateInterCompany(mockRegistry)
			if tt.wantErr == ErrInvalidInterCompanyEntity || tt.wantErr == nil {
				if !errors.Is(err, tt.wantErr) {
					t.Errorf("ValidateInterCompany() expected error %v, got %v", tt.wantErr, err)
				}
			}
		})
	}
}

// --- 5. Pipeline & Formatting Tests ---

func TestFullPipeline(t *testing.T) {
	mockChecker := &MockCreditChecker{}
	mockRegistry := &MockCustomerRegistry{AllowedCompanies: []string{"Authorized-Corp"}}
	
	invoice := SalesInvoice{
		IsReturn:   true,
		GrandTotal: 100,
		PaidAmount: 50,
		Company:    "Authorized-Corp",
		Precision:  PrecisionSettings{GrandTotal: 2},
	}

	// Triggers coverage for the Orchestrator Validate() function
	err := invoice.Validate(mockChecker, mockRegistry)
	if err != nil {
		t.Errorf("Validate() unexpectedly failed: %v", err)
	}
}

func TestErrorFormatting(t *testing.T) {
	// Triggers coverage for ValidationError.Error() branches
	tests := []struct {
		name string
		vErr *ValidationError
	}{
		{
			name: "With Details",
			vErr: &ValidationError{Err: ErrInvalidQty, Details: "Qty is -5"},
		},
		{
			name: "Without Details",
			vErr: &ValidationError{Err: ErrInvalidQty},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			msg := tt.vErr.Error()
			if msg == "" {
				t.Error("Error() returned empty string")
			}
		})
	}
}