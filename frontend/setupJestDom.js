require('@testing-library/jest-dom')
require('whatwg-fetch')

// Mock localStorage
const localStorageMock = {
  store: {},
  getItem: jest.fn((key) => localStorageMock.store[key] || null),
  setItem: jest.fn((key, value) => {
    localStorageMock.store[key] = String(value)
  }),
  removeItem: jest.fn((key) => {
    delete localStorageMock.store[key]
  }),
  clear: jest.fn(() => {
    localStorageMock.store = {}
  })
}

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true
})

// Mock matchMedia
window.matchMedia = window.matchMedia || ((query) => ({
  matches: false,
  media: query,
  onchange: null,
  addListener: () => {},
  removeListener: () => {},
  addEventListener: () => {},
  removeEventListener: () => {},
  dispatchEvent: () => {}
}))

// Mock ResizeObserver
window.ResizeObserver = window.ResizeObserver || class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// Mock IntersectionObserver
window.IntersectionObserver = window.IntersectionObserver || class IntersectionObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// Mock getComputedStyle
window.getComputedStyle = window.getComputedStyle || (() => ({
  getPropertyValue: () => ''
}))

// Mock clipboard API
window.navigator.clipboard = window.navigator.clipboard || {
  writeText: jest.fn(() => Promise.resolve()),
  readText: jest.fn(() => Promise.resolve())
}

// Mock HTMLElement methods
window.HTMLElement.prototype.scrollIntoView = window.HTMLElement.prototype.scrollIntoView || (() => {})
window.HTMLElement.prototype.scrollTo = window.HTMLElement.prototype.scrollTo || (() => {})
window.HTMLElement.prototype.scroll = window.HTMLElement.prototype.scroll || (() => {})

// Mock HTMLElement properties
Object.defineProperties(window.HTMLElement.prototype, {
  offsetLeft: { value: 0 },
  offsetTop: { value: 0 },
  offsetHeight: { value: 0 },
  offsetWidth: { value: 0 }
})