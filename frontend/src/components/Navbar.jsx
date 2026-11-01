/**
 * @file Navbar.jsx
 * @description Barra de navegación institucional con acceso a las secciones del SGI TECBA.
 * @author Equipo Frontend - SGI TECBA
 */

import { useState } from 'react';

const SECCIONES = [
    { href: '#/', path: '/', label: 'Inicio' },
    { href: '#/rubros', path: '/rubros', label: 'Rubros' },
    { href: '#/cobertura', path: '/cobertura', label: 'Cobertura' },
    { href: '#/fuentes', path: '/fuentes', label: 'Fuentes' },
];

const estiloEnlace = (activo) => ({
    padding: '0.5rem 1rem',
    fontWeight: 600,
    color: activo ? '#1d3557' : '#2c3e50',
    borderBottom: activo ? '2px solid #1d3557' : '2px solid transparent',
    textDecoration: 'none',
    borderRadius: 0,
});

export const Navbar = ({ currentPath = '/' }) => {
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const esInicio = currentPath === '/';

    return (
        <header className="o-header navbar bg-white" style={{ borderBottom: '4px solid #F6C243' }} role="banner">
            <a href="#main" className="skip-to-main-content-link">
                Saltar al contenido principal
            </a>

            <div className="container header-container d-flex align-items-center flex-wrap">
                <a href="#/" className="navbar-brand me-4" aria-label="Ir al inicio del SGI TECBA">
                    <img
                        src="/logo_ba_corto.png"
                        alt="Gobierno de la Ciudad de Buenos Aires - Inicio"
                        style={{ height: '200px' }}
                    />
                </a>

                <div className="d-none d-lg-flex align-items-center">
                    <nav aria-label="Navegación principal">
                        <ul className="nav nav-pills nav-sections mb-0 d-flex flex-row align-items-center gap-1">
                            {SECCIONES.map((seccion) => {
                                const activo = seccion.path === currentPath || (seccion.path === '/' && esInicio);
                                return (
                                    <li className="nav-item" key={seccion.path}>
                                        <a
                                            className="nav-link"
                                            href={seccion.href}
                                            style={estiloEnlace(activo)}
                                            aria-current={activo ? 'page' : undefined}
                                        >
                                            {seccion.label}
                                        </a>
                                    </li>
                                );
                            })}
                        </ul>
                    </nav>
                </div>

                <button
                    className={`navbar-toggler ms-auto d-lg-none ${isMenuOpen ? '' : 'collapsed'}`}
                    type="button"
                    onClick={() => setIsMenuOpen(!isMenuOpen)}
                    aria-expanded={isMenuOpen}
                    aria-label="Abrir menú de navegación"
                >
                    <span className="navbar-toggler-icon"></span>
                </button>

                {isMenuOpen && (
                    <div className="w-100 d-lg-none mt-3 p-3 bg-white border rounded shadow-sm text-center">
                        <ul className="nav flex-column gap-2 mb-0">
                            {SECCIONES.map((seccion) => {
                                const activo = seccion.path === currentPath || (seccion.path === '/' && esInicio);
                                return (
                                    <li className="nav-item" key={seccion.path}>
                                        <a
                                            className="nav-link text-dark"
                                            href={seccion.href}
                                            onClick={() => setIsMenuOpen(false)}
                                            style={{ fontWeight: 600, color: activo ? '#1d3557' : undefined }}
                                            aria-current={activo ? 'page' : undefined}
                                        >
                                            {seccion.label}
                                        </a>
                                    </li>
                                );
                            })}
                        </ul>
                    </div>
                )}
            </div>
        </header>
    );
};
