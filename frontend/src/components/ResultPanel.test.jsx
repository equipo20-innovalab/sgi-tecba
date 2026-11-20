import { render, screen, waitFor } from '@testing-library/react';
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { ResultPanel } from './ResultPanel';

describe('Pruebas de ResultPanel con Datos Simulados y Mock de API USIG', () => {

  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              comuna: 'Comuna 1',
              barrio: 'San Nicolás',
              seccion: '005',
              manzana: '042',
              parcela: '012A',
            }),
        })
      )
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test('1. Muestra el mensaje de bienvenida cuando aún no hay datos (data es null)', () => {
    render(<ResultPanel data={null} />);

    expect(screen.getByText('Resultado de la consulta')).toBeTruthy();
    expect(screen.getByText(/Ingresá una actividad y una dirección/i)).toBeTruthy();
  });

  test('2. Renderiza correctamente una respuesta completa simulada del backend y enriquece con USIG', async () => {
    const mockRespuestaExitosa = {
      ubicacion: {
        direccion_normalizada: 'AV. CORRIENTES 1234',
        comuna: 1,
      },
      ficha_catastral: {
        superficie_total: 150,
        smp: '005-042-012A',
      },
      habilitaciones_parcela: [
        { comuna_fuente: 'catastro', smp_fuente: 'catastro' }
      ],
      contexto_territorial: {
        total_habilitaciones: 4520,
      },
      actividad_detectada: 'Cafetería y Bar',
    };

    render(<ResultPanel data={mockRespuestaExitosa} />);

    expect(screen.getByText('AV. CORRIENTES 1234')).toBeTruthy();
    expect(screen.getByText('Datos consultados')).toBeTruthy();
    expect(screen.getByText(/Catastro · Confianza Alta/i)).toBeTruthy();
    expect(screen.getByText(/150 m² · SMP 005-042-012A/i)).toBeTruthy();
    expect(screen.getByText('Cafetería y Bar')).toBeTruthy();

    await waitFor(() => {
      expect(screen.getByText(/Comuna 1 · San Nicolás/i)).toBeTruthy();
    });
  });

  test('3. Muestra alerta amarilla y cambia estado cuando el backend pide más información', async () => {
    const mockRespuestaIncompleta = {
      ubicacion: { direccion_original: 'Calle Falsa 123' },
      mensaje: 'No se encontró la parcela exacta. Por favor verificá la altura.',
    };

    render(<ResultPanel data={mockRespuestaIncompleta} />);

    expect(screen.getByText('Calle Falsa 123')).toBeTruthy();
    expect(screen.getByText('Requiere más información')).toBeTruthy();
    expect(screen.getByText(/No se encontró la parcela exacta/i)).toBeTruthy();
  });

  test('4. Maneja correctamente si la API externa de USIG falla o no devuelve datos', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new Error('Error de red USIG')))
    );

    const mockSinUsig = {
      ubicacion: {
        direccion_normalizada: 'AV. SANTA FE 3200',
        comuna: 14,
      },
    };

    render(<ResultPanel data={mockSinUsig} />);

    await waitFor(() => {
      expect(screen.getByText('Comuna 14')).toBeTruthy();
    });
  });
});