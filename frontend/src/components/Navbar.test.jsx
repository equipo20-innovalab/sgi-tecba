import { render, screen, fireEvent } from '@testing-library/react';
import { describe, test, expect } from 'vitest';
import { Navbar } from './Navbar';

describe('Pruebas de Navegación en Navbar (Actualizado)', () => {

  test('1. Renderiza todas las secciones principales con sus rutas href correctas', () => {
    render(<Navbar currentPath="/" />);

    const enlacesEsperados = [
      { nombre: 'Inicio', ruta: '#/' },
      { nombre: 'Rubros', ruta: '#/rubros' },
      { nombre: 'Cobertura', ruta: '#/cobertura' },
      { nombre: 'Fuentes', ruta: '#/fuentes' },
    ];

    enlacesEsperados.forEach(({ nombre, ruta }) => {
      const enlace = screen.getByRole('link', { name: nombre });
      expect(enlace).toBeTruthy();
      expect(enlace.getAttribute('href')).toBe(ruta);
    });
  });

  test('2. Marca correctamente la sección activa según la prop currentPath', () => {
    render(<Navbar currentPath="/rubros" />);

    const enlaceRubros = screen.getByRole('link', { name: 'Rubros' });
    const enlaceInicio = screen.getByRole('link', { name: 'Inicio' });

    expect(enlaceRubros.getAttribute('aria-current')).toBe('page');
    expect(enlaceInicio.getAttribute('aria-current')).toBeNull();
  });

  test('3. Abre y cierra el menú desplegable móvil al interactuar con el botón', () => {
    render(<Navbar currentPath="/" />);

    const botonMenu = screen.getByRole('button', { name: /Abrir menú de navegación/i });
    expect(botonMenu.getAttribute('aria-expanded')).toBe('false');

    fireEvent.click(botonMenu);
    expect(botonMenu.getAttribute('aria-expanded')).toBe('true');

    const enlacesInicio = screen.getAllByRole('link', { name: 'Inicio' });
    expect(enlacesInicio.length).toBe(2);

    fireEvent.click(enlacesInicio[1]);
    expect(botonMenu.getAttribute('aria-expanded')).toBe('false');
  });

  test('4. Renderiza el nuevo logo institucional y el enlace de accesibilidad', () => {
    render(<Navbar />);

    const logo = screen.getByAltText('Habilitacion Inteligente - Inicio');
    expect(logo).toBeTruthy();
    expect(logo.getAttribute('src')).toBe('/logo_ba_corto.png');

    const enlaceLogo = screen.getByLabelText('Ir al inicio del SGI TECBA');
    expect(enlaceLogo).toBeTruthy();

    const skipLink = screen.getByText('Saltar al contenido principal');
    expect(skipLink.getAttribute('href')).toBe('#main');
  });
});