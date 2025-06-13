import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import ExperimentCreationModal from "./ExperimentCreationModal"
import React from "react"

// Mock global fetch
const mockFetch = jest.fn()
// @ts-ignore
global.fetch = mockFetch

afterEach(() => {
  jest.resetAllMocks()
})

describe("ExperimentCreationModal", () => {
  const defaultProps = {
    isOpen: true,
    onClose: jest.fn(),
  }

  test("renders modal with fields", () => {
    render(<ExperimentCreationModal {...defaultProps} />)

    expect(screen.getByText(/Create New A\/B Experiment/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Experiment Name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Description/i)).toBeInTheDocument()
    // Variant selector row exists
    expect(screen.getByText(/Variants/i)).toBeInTheDocument()
  })

  test("submits form when data valid", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: 1 }),
    })
    render(<ExperimentCreationModal {...defaultProps} />)

    fireEvent.change(screen.getByLabelText(/Experiment Name/i), {
      target: { value: "Test Exp" },
    })

    // Fill allocations sum to 100 (default 0.5 + 0.5 already)
    // Select dummy model ids
    const selects = screen.getAllByRole("combobox")
    selects.forEach((sel) => {
      fireEvent.change(sel, { target: { value: "1" } })
    })

    fireEvent.click(screen.getByRole("button", { name: /Create Experiment/i }))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled()
    })

    const payload = JSON.parse(mockFetch.mock.calls[0][1].body)
    expect(payload.name).toBe("Test Exp")
    expect(payload.variants.length).toBeGreaterThan(0)
  })

  test("shows validation error when traffic not 100%", () => {
    render(<ExperimentCreationModal {...defaultProps} />)

    // Change allocation for first variant to 0.3, second stays 0.5 => sum 0.8
    const inputs = screen.getAllByRole("spinbutton")
    fireEvent.change(inputs[0], { target: { value: "0.3" } })

    // Attempt submit
    fireEvent.click(screen.getByRole("button", { name: /Create Experiment/i }))

    expect(
      screen.getByText(/Traffic allocations must sum to 100%/i)
    ).toBeInTheDocument()
  })
}) 