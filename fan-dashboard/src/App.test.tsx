import { render, screen } from '@testing-library/react';
import App from './App';

test('renders tunnel fan monitoring title', () => {
  render(<App />);
  const titleElement = screen.getByText(/Tunnel Fan Monitoring/i);
  expect(titleElement).toBeInTheDocument();
});


