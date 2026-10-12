/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                gcba: {
                    primary: '#1d3557',     // Azul institucional principal (inspirado en portales GCBA)
                    secondary: '#457b9d',   // Azul secundario / acentos
                    light: '#f1faee',       // Fondo claro de soporte
                    dark: '#1d2a3a',        // Texto principal oscuro
                    accent: '#e63946',      // Alertas o puntos focales de interacción
                    surface: '#ffffff',     // Superficie de tarjetas / contenedores
                }
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
            },
        },
    },
    plugins: [],
}