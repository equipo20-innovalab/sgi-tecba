import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, test, expect, vi } from 'vitest';
import { SearchBox } from './SearchBox';

describe('Pruebas unitarias y Mocking de SearchBox (Actualizado)', () => {
  
  test('1. Renderiza correctamente el título y el nuevo campo de búsqueda', () => {
    render(<SearchBox onSearch={() => {}} />);

    expect(screen.getByText('Sistema de Gestión Inteligente')).toBeTruthy();
    const input = screen.getByPlaceholderText(/Ej: Quiero abrir una cafetería en Corrientes al 2500/i);
    expect(input).toBeTruthy();
  });

  test('2. Envía la consulta al hacer clic en Buscar (Mocking de onSearch)', () => {
    const mockOnSearch = vi.fn();
    render(<SearchBox onSearch={mockOnSearch} />);

    const input = screen.getByPlaceholderText(/Ej: Quiero abrir una cafetería/i);
    const botonBuscar = screen.getByRole('button', { name: /Buscar/i });

    fireEvent.change(input, { target: { value: 'Zonificación R2A en Belgrano' } });
    fireEvent.click(botonBuscar);

    expect(mockOnSearch).toHaveBeenCalledTimes(1);
    expect(mockOnSearch).toHaveBeenCalledWith('Zonificación R2A en Belgrano');
  });

  test('3. No permite enviar búsquedas vacías o solo con espacios', () => {
    const mockOnSearch = vi.fn();
    render(<SearchBox onSearch={mockOnSearch} />);

    const input = screen.getByPlaceholderText(/Ej: Quiero abrir una cafetería/i);
    const botonBuscar = screen.getByRole('button', { name: /Buscar/i });

    fireEvent.click(botonBuscar);
    fireEvent.change(input, { target: { value: '   ' } });
    fireEvent.click(botonBuscar);

    expect(mockOnSearch).not.toHaveBeenCalled();
  });

  test('4. Simula la búsqueda por voz y autocompleta el texto tras 2 segundos', () => {
    vi.useFakeTimers();
    render(<SearchBox onSearch={() => {}} />);

    const botonVoz = screen.getByRole('button', { name: /Voz/i });
    const input = screen.getByPlaceholderText(/Ej: Quiero abrir una cafetería/i);

    fireEvent.click(botonVoz);
    expect(screen.getByText('Escuchando...')).toBeTruthy();

    act(() => {
      vi.advanceTimersByTime(2000);
    });

    expect(input.value).toBe('Evaluación de local comercial en Av. Corrientes');
    expect(screen.getByText('Voz')).toBeTruthy();
    vi.useRealTimers();
  });

  test('5. Deshabilita los controles cuando está esperando respuesta del backend (isLoading)', () => {
    render(<SearchBox onSearch={() => {}} isLoading={true} />);

    const botonConsultando = screen.getByRole('button', { name: /Consultando.../i });
    const botonVoz = screen.getByRole('button', { name: /Voz/i });

    expect(botonConsultando.disabled).toBe(true);
    expect(botonVoz.disabled).toBe(true);
  });

  test('6. [NUEVO] Muestra el botón de limpiar (X) solo al escribir y borra el texto al hacer clic', () => {
    render(<SearchBox onSearch={() => {}} />);
    const input = screen.getByPlaceholderText(/Ej: Quiero abrir una cafetería/i);

    // Al principio el botón X no debe existir
    expect(screen.queryByLabelText('Borrar texto de búsqueda')).toBeNull();

    // Al escribir texto aparece el botón X
    fireEvent.change(input, { target: { value: 'Panadería' } });
    const botonLimpiar = screen.getByLabelText('Borrar texto de búsqueda');
    expect(botonLimpiar).toBeTruthy();

    // Al hacer clic limpia el campo y desaparece el botón
    fireEvent.click(botonLimpiar);
    expect(input.value).toBe('');
    expect(screen.queryByLabelText('Borrar texto de búsqueda')).toBeNull();
  });

  test('7. [NUEVO] Limpia el campo de búsqueda al presionar la tecla Escape', () => {
    render(<SearchBox onSearch={() => {}} />);
    const input = screen.getByPlaceholderText(/Ej: Quiero abrir una cafetería/i);

    fireEvent.change(input, { target: { value: 'Restaurante en Palermo' } });
    expect(input.value).toBe('Restaurante en Palermo');

    fireEvent.keyDown(input, { key: 'Escape', code: 'Escape' });
    expect(input.value).toBe('');
  });
});
