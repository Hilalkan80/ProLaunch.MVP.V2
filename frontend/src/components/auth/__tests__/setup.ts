import { render } from '@testing-library/react'
import { Wrapper } from './Wrapper'

const customRender = (ui, options = {}) => render(ui, { wrapper: Wrapper, ...options })

export * from '@testing-library/react'
export { customRender as render }