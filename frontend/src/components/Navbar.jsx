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
    padding: '0.5rem 0.9rem',
    fontWeight: 600,
    fontSize: '15px',
    color: activo ? '#0b2033' : '#1e3a4c',
    backgroundColor: 'transparent',
    borderBottom: activo ? '3px solid #ffc600' : '3px solid transparent',
    textDecoration: 'none',
    borderRadius: 0,
});

export const Navbar = ({ currentPath = '/' }) => {
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const esInicio = currentPath === '/';

    return (
        <header
            className="o-header navbar sgi-nav-transparente"
            style={{ padding: '14px 16px', borderBottom: 'none' }}
            role="banner"
        >
            <style>{`
                header.sgi-nav-transparente {
                    background-color: transparent !important;
                    background-image: none !important;
                    box-shadow: none !important;
                }
                .sgi-nav-links .nav-link:hover,
                .sgi-nav-links .nav-link:focus,
                .sgi-nav-links .nav-link:focus-visible,
                .sgi-nav-links .nav-link:active {
                    outline: none !important;
                    box-shadow: none !important;
                    background-color: transparent !important;
                    text-decoration: none !important;
                }
            `}</style>
            <a href="#main" className="skip-to-main-content-link">
                Saltar al contenido principal
            </a>

            <div className="container header-container d-flex align-items-center flex-wrap">
            <a 
                href="#/" 
                className="navbar-brand me-4 d-flex align-items-center" 
                style={{ outline: 'none', boxShadow: 'none', border: 'none' }}
                aria-label="Ir al inicio del SGI TECBA"
            >
                <img
                    src="/logo_habilitacion.png"
                    alt="Habilitación Inteligente - Inicio"
                    style={{ height: '44px', width: 'auto', display: 'block' }}
                />
            </a>

                <div className="d-none d-lg-flex align-items-center ms-auto">
                    <nav aria-label="Navegación principal">
                        <ul className="nav nav-pills nav-sections sgi-nav-links mb-0 d-flex flex-row align-items-center gap-1">
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
                    <div className="w-100 d-lg-none mt-3 p-3 border rounded shadow-sm text-center sgi-nav-transparente">
                        <ul className="nav flex-column gap-2 mb-0 sgi-nav-links">
                            {SECCIONES.map((seccion) => {
                                const activo = seccion.path === currentPath || (seccion.path === '/' && esInicio);
                                return (
                                    <li className="nav-item" key={seccion.path}>
                                        <a
                                            className="nav-link text-dark"
                                            href={seccion.href}
                                            onClick={() => setIsMenuOpen(false)}
                                            style={{ fontWeight: 600, color: activo ? '#0b2033' : '#1e3a4c' }}
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
