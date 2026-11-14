import { render } from '@testing-library/react';
import { describe, test, expect, vi } from 'vitest';
import App from './App';

// Simulamos MapLibre GL usando clases reales para soportar "new"
vi.mock('maplibre-gl', () => {
  class MockMap {
    on = vi.fn();
    off = vi.fn();
    remove = vi.fn();
    addControl = vi.fn();
    addSource = vi.fn();
    addLayer = vi.fn();
    getSource = vi.fn();
    getLayer = vi.fn();
    setLayoutProperty = vi.fn();
    setPaintProperty = vi.fn();
    flyTo = vi.fn();
    resize = vi.fn();
  }

  class MockNavigationControl {}

  class MockMarker {
    setLngLat = vi.fn().mockReturnThis();
    setPopup = vi.fn().mockReturnThis();
    addTo = vi.fn().mockReturnThis();
    remove = vi.fn();
  }

  class MockPopup {
    setHTML = vi.fn().mockReturnThis();
    setText = vi.fn().mockReturnThis();
  }

  const mapMock = {
    Map: vi.fn(MockMap),
    NavigationControl: vi.fn(MockNavigationControl),
    Marker: vi.fn(MockMarker),
    Popup: vi.fn(MockPopup),
    setWorkerUrl: vi.fn(),
  };

  return {
    ...mapMock,
    default: mapMock,
  };
});

describe('Pruebas iniciales del MVP', () => {
  test('La aplicación principal renderiza sin errores', () => {
    const { container } = render(<App />);
    expect(container).toBeTruthy();
  });
});
