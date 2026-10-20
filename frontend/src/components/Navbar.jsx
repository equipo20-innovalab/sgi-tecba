/**
 * @file Navbar.jsx
 * @description Componente de barra de navegación adaptado al diseño de Figma (Obelisco v2).
 * @author Equipo Frontend - SGI TECBA
 */

import React, { useState } from 'react';

export const Navbar = () => {
    const [isMenuOpen, setIsMenuOpen] = useState(false);

    return (
        <header className="o-header navbar bg-white" style={{ borderBottom: '4px solid #F6C243' }} role="banner">
            <a href="#main" className="skip-to-main-content-link">
                Saltar al contenido principal
            </a>
            
            <div className="container header-container d-flex align-items-center flex-wrap">
                
                {/* Logo */}
                <a href="/" className="navbar-brand me-4">
                    <img 
                        src="/logo_ba_corto.png" 
                        alt="Gobierno de la Ciudad de Buenos Aires - Inicio" 
                        style={{ height: '200px' }} 
                    />
                </a>
                
                {/* MENÚ ESCRITORIO */}
                <div className="d-none d-lg-flex align-items-center">
                    <nav>
                        <ul className="nav nav-pills nav-sections mb-0 d-flex flex-row align-items-center gap-1">
                            <li className="nav-item">
                                <a className="nav-link" href="#navegacion" style={{ padding: '0.5rem 1rem', fontWeight: 600, color: '#2c3e50' }}>
                                    Navegación
                                </a>
                            </li>
                            <li className="dropdown">
                                <button
                                    type="button"
                                    className="btn btn-dropdown d-flex align-items-center bg-transparent border-0 shadow-none"
                                    data-bs-toggle="dropdown"
                                    aria-expanded="false"
                                    style={{ padding: '0.5rem 1rem', fontWeight: 600, color: '#2c3e50' }}
                                >
                                    <span className="btn-dropdown-text">Zonas</span>
                                    <span className="material-symbols-rounded btn-dropdown-icon ms-1" style={{ fontSize: '20px' }}>
                                        expand_more
                                    </span>
                                </button>
                                <div className="dropdown-menu">
                                    <a className="dropdown-item" href="#norte">Zona Norte</a>
                                    <a className="dropdown-item" href="#sur">Zona Sur</a>
                                </div>
                            </li>
                            <li className="nav-item">
                                <a className="nav-link" href="#fuentes" style={{ padding: '0.5rem 1rem', fontWeight: 600, color: '#2c3e50' }}>
                                    Fuentes oficiales
                                </a>
                            </li>
                        </ul>
                    </nav>
                </div>

                {/* Boton hamburguesa */}
                <button
                    className={`navbar-toggler ms-auto d-lg-none ${isMenuOpen ? '' : 'collapsed'}`}
                    type="button"
                    onClick={() => setIsMenuOpen(!isMenuOpen)}
                >
                    <span className="navbar-toggler-icon"></span>
                </button>

                {/* Menu celulares */}
                {isMenuOpen && (
                    <div className="w-100 d-lg-none mt-3 p-3 bg-white border rounded shadow-sm text-center">
                        <ul className="nav flex-column gap-2 mb-0">
                            
                            <li className="nav-item">
                                <a className="nav-link text-dark" href="#navegacion" style={{ fontWeight: 600 }}>
                                    Navegación
                                </a>
                            </li>
                            
                            <li className="nav-item">
                                <div className="dropdown w-100">
                                    <button
                                        type="button"
                                        className="nav-link d-flex align-items-center justify-content-center bg-transparent border-0 shadow-none text-dark w-100"
                                        data-bs-toggle="dropdown"
                                        aria-expanded="false"
                                        style={{ fontWeight: 600 }}
                                    >
                                        <span className="btn-dropdown-text" style={{ marginLeft: '24px' }}>Zonas</span>
                                        <span className="material-symbols-rounded ms-1" style={{ fontSize: '20px' }}>
                                            expand_more
                                        </span>
                                    </button>
                                    
                                    <div className="dropdown-menu w-100 text-center border-0 bg-light mt-2">
                                        <a className="dropdown-item" href="#norte">Zona Norte</a>
                                        <a className="dropdown-item" href="#sur">Zona Sur</a>
                                    </div>
                                </div>
                            </li>

                            <li className="nav-item">
                                <a className="nav-link text-dark" href="#fuentes" style={{ fontWeight: 600 }}>
                                    Fuentes oficiales
                                </a>
                            </li>
                            
                        </ul>
                    </div>
                )}
                
            </div>
        </header>
    );
};