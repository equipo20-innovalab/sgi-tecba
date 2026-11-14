import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, test, expect, vi, afterEach } from 'vitest';
import { SearchBox } from './SearchBox';

describe('Pruebas unitarias y Mocking de SearchBox', () => {
  
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  test('1. Renderiza correctamente el título y el campo de búsqueda', () => {
    render(<SearchBox />);
    
    expect(screen.getByText('Sistema de Gestión Inteligente')).toBeTruthy();
    expect(screen.getByPlaceholderText(/Apto cafetería en Palermo/i)).toBeTruthy();
  });

  test('2. Envía la consulta al hacer clic en Buscar (Mocking de onSearch)', () => {
    // Simulamos la función que se conectaría al backend
    const mockOnSearch = vi.fn();
    render(<SearchBox onSearch={mockOnSearch} />);

    const input = screen.getByPlaceholderText(/Apto cafetería en Palermo/i);
    const botonBuscar = screen.getByRole('button', { name: /Buscar/i });

    // Simulamos que el usuario escribe y envía el formulario
    fireEvent.change(input, { target: { value: 'Zonificación R2A en Belgrano' } });
    fireEvent.click(botonBuscar);

    // Verificamos que se llamó 1 vez con el texto exacto
    expect(mockOnSearch).toHaveBeenCalledTimes(1);
    expect(mockOnSearch).toHaveBeenCalledWith('Zonificación R2A en Belgrano');
  });

  test('3. No permite enviar búsquedas vacías o solo con espacios', () => {
    const mockOnSearch = vi.fn();
    render(<SearchBox onSearch={mockOnSearch} />);

    const input = screen.getByPlaceholderText(/Apto cafetería en Palermo/i);
    const botonBuscar = screen.getByRole('button', { name: /Buscar/i });

    fireEvent.change(input, { target: { value: '    ' } });
    fireEvent.click(botonBuscar);

    expect(mockOnSearch).not.toHaveBeenCalled();
  });

  test('4. Simula la búsqueda por voz y autocompleta el texto tras 2 segundos', () => {
    // Activamos el reloj simulado de Vitest para no esperar 2 segundos reales
    vi.useFakeTimers();
    render(<SearchBox />);

    const botonVoz = screen.getByRole('button', { name: /Voz/i });
    const input = screen.getByPlaceholderText(/Apto cafetería en Palermo/i);

    // Hacemos clic en Voz
    fireEvent.click(botonVoz);
    expect(screen.getByText('Escuchando...')).toBeTruthy();

    // Adelantamos el tiempo simulado 2000 milisegundos
    act(() => {
      vi.advanceTimersByTime(2000);
    });

    // Comprobamos que se autocompletó el texto y volvió a decir "Voz"
    expect(input.value).toBe('Evaluación de local comercial en Av. Corrientes');
    expect(screen.getByText('Voz')).toBeTruthy();
  });

  test('5. Deshabilita los controles cuando está esperando respuesta del backend (isLoading)', () => {
    render(<SearchBox isLoading={true} />);

    const botonConsultando = screen.getByRole('button', { name: /Consultando.../i });
    const botonVoz = screen.getByTitle(/Consulta por voz/i);

    expect(botonConsultando.disabled).toBe(true);
    expect(botonVoz.disabled).toBe(true);
  });
});
