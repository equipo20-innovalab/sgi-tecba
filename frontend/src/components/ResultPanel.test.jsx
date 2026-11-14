import { render, screen } from '@testing-library/react';
import { describe, test, expect } from 'vitest';
import { ResultPanel } from './ResultPanel';

describe('Pruebas de ResultPanel con Datos Simulados (Mocking)', () => {
  
  test('1. Muestra el mensaje de bienvenida cuando aún no hay datos (data es null)', () => {
    render(<ResultPanel data={null} />);

    expect(screen.getByText('Resultado de la consulta')).toBeTruthy();
    expect(screen.getByText(/Ingresá una actividad y una dirección/i)).toBeTruthy();
  });

  test('2. Renderiza correctamente una respuesta completa simulada del backend', () => {
    // Simulamos el JSON real que devolvería la API del SGI TECBA
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

    // Verificamos que todos los datos simulados se dibujen bien
    expect(screen.getByText('AV. CORRIENTES 1234')).toBeTruthy();
    expect(screen.getByText('Datos consultados')).toBeTruthy();
    expect(screen.getByText('Comuna 1')).toBeTruthy();
    expect(screen.getByText(/Catastro · Confianza Alta/i)).toBeTruthy();
    expect(screen.getByText('150 m²')).toBeTruthy();
    expect(screen.getByText('Cafetería y Bar')).toBeTruthy();
  });

  test('3. Muestra alerta amarilla y cambia estado cuando el backend pide más información', () => {
    const mockRespuestaIncompleta = {
      ubicacion: { direccion_original: 'Calle Falsa 123' },
      mensaje: 'No se encontró la parcela exacta. Por favor verificá la altura.',
    };

    render(<ResultPanel data={mockRespuestaIncompleta} />);

    expect(screen.getByText('Calle Falsa 123')).toBeTruthy();
    expect(screen.getByText('Requiere más información')).toBeTruthy();
    expect(screen.getByText(/No se encontró la parcela exacta/i)).toBeTruthy();
  });

  test('4. Calcula y muestra correctamente las métricas de cobertura del padrón', () => {
    const mockConCobertura = {
      ubicacion: { direccion_normalizada: 'AV. SANTA FE 3200' },
      cobertura_datos: {
        total_registros: 1200,
        campos: {
          comuna: { cobertura: 0.95, expectativa_minima: 0.90, cumple_expectativa: true },
          smp: { cobertura: 0.70, expectativa_minima: 0.85, cumple_expectativa: false },
        },
      },
    };

    render(<ResultPanel data={mockConCobertura} />);

    expect(screen.getByText('Cobertura del padrón')).toBeTruthy();
    expect(screen.getByText('95.0%')).toBeTruthy();
    expect(screen.getByText(/Cumple de la expectativa de 90%/i)).toBeTruthy();
    expect(screen.getByText('70.0%')).toBeTruthy();
    expect(screen.getByText(/Debajo de la expectativa de 85%/i)).toBeTruthy();
  });
});
