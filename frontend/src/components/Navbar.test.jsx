import { render, screen, fireEvent } from '@testing-library/react';
import { describe, test, expect } from 'vitest';
import { Navbar } from './Navbar';

describe('Pruebas de Navegación en Navbar', () => {
  
  test('1. Renderiza todas las secciones principales con sus rutas href correctas', () => {
    render(<Navbar />);

    const seccionesEsperadas = [
      { label: 'Inicio', href: '#/' },
      { label: 'Rubros', href: '#/rubros' },
      { label: 'Cobertura', href: '#/cobertura' },
      { label: 'Fuentes', href: '#/fuentes' },
    ];

    seccionesEsperadas.forEach(({ label, href }) => {
      const enlace = screen.getByRole('link', { name: label });
      expect(enlace).toBeTruthy();
      expect(enlace.getAttribute('href')).toBe(href);
    });
  });

  test('2. Marca correctamente la sección activa según la prop currentPath', () => {
    render(<Navbar currentPath="/rubros" />);

    const enlaceRubros = screen.getByRole('link', { name: 'Rubros' });
    const enlaceInicio = screen.getByRole('link', { name: 'Inicio' });

    // Verificamos que Rubros tenga el atributo de página activa y Inicio no
    expect(enlaceRubros.getAttribute('aria-current')).toBe('page');
    expect(enlaceInicio.getAttribute('aria-current')).toBeNull();
  });

  test('3. Abre y cierra el menú desplegable móvil al interactuar con el botón', () => {
    render(<Navbar />);

    const botonMenu = screen.getByRole('button', { name: /Abrir menú de navegación/i });
    
    // Al principio el menú debe estar cerrado
    expect(botonMenu.getAttribute('aria-expanded')).toBe('false');

    // Hacemos clic para abrir el menú móvil
    fireEvent.click(botonMenu);
    expect(botonMenu.getAttribute('aria-expanded')).toBe('true');

    // Al abrirse, aparecen los enlaces duplicados en el menú móvil
    const enlacesCobertura = screen.getAllByRole('link', { name: 'Cobertura' });
    expect(enlacesCobertura.length).toBe(2);

    // Hacemos clic en el enlace del menú móvil y comprobamos que el menú se cierra solo
    fireEvent.click(enlacesCobertura[1]);
    expect(botonMenu.getAttribute('aria-expanded')).toBe('false');
  });

  test('4. Renderiza el logo institucional y el enlace de accesibilidad', () => {
    render(<Navbar />);

    const logo = screen.getByAltText(/Gobierno de la Ciudad de Buenos Aires - Inicio/i);
    const skipLink = screen.getByText(/Saltar al contenido principal/i);

    expect(logo).toBeTruthy();
    expect(skipLink.getAttribute('href')).toBe('#main');
  });
});
