import '@testing-library/jest-dom'
import * as React from 'react'

// Mock localStorage
const mockLocalStorage = {
  store: {},
  getItem: jest.fn((key) => mockLocalStorage.store[key] || null),
  setItem: jest.fn((key, value) => {
    mockLocalStorage.store[key] = String(value)
  }),
  removeItem: jest.fn((key) => {
    delete mockLocalStorage.store[key]
  }),
  clear: jest.fn(() => {
    mockLocalStorage.store = {}
  })
}

window.localStorage = mockLocalStorage
global.localStorage = mockLocalStorage

// Mock matchMedia
window.matchMedia = jest.fn().mockImplementation(query => ({
  matches: false,
  media: query,
  onchange: null,
  addListener: jest.fn(),
  removeListener: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  dispatchEvent: jest.fn()
}))

// Mock ResizeObserver
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

window.ResizeObserver = ResizeObserver

// Mock IntersectionObserver
class IntersectionObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

window.IntersectionObserver = IntersectionObserver

// Mock window.scrollTo
window.scrollTo = jest.fn()

// Mock window.getSelection
window.getSelection = jest.fn().mockImplementation(() => ({
  addRange: jest.fn(),
  removeAllRanges: jest.fn(),
  getRangeAt: jest.fn(),
  removeRange: jest.fn()
}))

// Mock Element.prototype methods
Element.prototype.scrollIntoView = jest.fn()
Element.prototype.scrollTo = jest.fn()
Element.prototype.scroll = jest.fn()

// Mock HTMLElement properties
Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
  configurable: true,
  value: 100
})

Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {
  configurable: true,
  value: 100
})

Object.defineProperty(HTMLElement.prototype, 'offsetTop', {
  configurable: true,
  value: 100
})

Object.defineProperty(HTMLElement.prototype, 'offsetLeft', {
  configurable: true,
  value: 100
})

// Mock fetch
global.fetch = jest.fn().mockImplementation(() => Promise.resolve({
  ok: true,
  json: () => Promise.resolve({}),
  text: () => Promise.resolve(''),
  blob: () => Promise.resolve(new Blob())
}))

// Clean up after each test
afterEach(() => {
  jest.clearAllMocks()
  mockLocalStorage.store = {}
})