/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        'integral': ['Integral CF', 'sans-serif'],
      },
      colors: {
        'vervestacks': {
          // New brand colors - updated palette
          primary: '#40517F', // Dark Blue
          secondary: '#C3D4FE', // Background Blue
          accent: '#FC8462', // Kanors Orange start
          
          // Kanors gradient colors
          'kanors-start': '#FC8462', // Orange start
          'kanors-end': '#F8B26A', // Orange end
          
          // Background and text colors
          background: '#C3D4FE', // Light blue background
          'dark-blue': '#40517F', // Dark blue for text/accents
          'country-color': '#6976AA', // Country color for map - matches screenshot
          
          // Extended palette for gradients
          'orange-light': '#F8B26A', // Light orange
          'orange-dark': '#FC8462', // Dark orange
          'blue-light': '#C3D4FE', // Light blue
          'blue-dark': '#40517F', // Dark blue
          
          // Semantic colors
          success: '#10B981', // Emerald
          warning: '#F59E0B', // Amber
          error: '#EF4444', // Red
          info: '#3B82F6', // Blue
          
          // Neutral colors
          dark: '#40517F', // Dark blue for text
          light: '#C3D4FE', // Light blue background
          
          // Extended palette
          'primary-light': '#C3D4FE',
          'primary-dark': '#40517F',
          'secondary-light': '#F8B26A',
          'secondary-dark': '#FC8462',
          'accent-light': '#F8B26A',
          'accent-dark': '#FC8462'
        }
      },
      
      // Enhanced gradient definitions - updated with new color palette
      backgroundImage: {
        // Primary gradients - Kanors orange gradient
        'gradient-primary': 'linear-gradient(135deg, #FC8462 0%, #F8B26A 100%)',
        'gradient-primary-hover': 'linear-gradient(135deg, #F8B26A 0%, #FC8462 100%)',
        'gradient-primary-light': 'linear-gradient(135deg, #F8B26A 0%, #FC8462 50%, #F8B26A 100%)',
        
        // Secondary gradients - Blue gradients
        'gradient-secondary': 'linear-gradient(135deg, #C3D4FE 0%, #40517F 100%)',
        'gradient-secondary-hover': 'linear-gradient(135deg, #40517F 0%, #C3D4FE 100%)',
        
        // Accent gradients - Orange gradients
        'gradient-accent': 'linear-gradient(135deg, #FC8462 0%, #F8B26A 100%)',
        'gradient-accent-hover': 'linear-gradient(135deg, #F8B26A 0%, #FC8462 100%)',
        
        // Semantic gradients
        'gradient-success': 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
        'gradient-warning': 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)',
        'gradient-error': 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)',
        'gradient-info': 'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)',
        
        // Special gradients - enhanced for better visual appeal
        'gradient-hero': 'linear-gradient(135deg, rgba(252, 132, 98, 0.95) 0%, rgba(248, 178, 106, 0.95) 100%)',
        'gradient-card': 'linear-gradient(135deg, #FFFFFF 0%, #C3D4FE 100%)',
        'gradient-overlay': 'linear-gradient(135deg, rgba(252, 132, 98, 0.1) 0%, rgba(248, 178, 106, 0.1) 100%)',
        
        // New Kanors-focused gradients
        'gradient-kanors': 'linear-gradient(135deg, #FC8462 0%, #F8B26A 100%)',
        'gradient-kanors-reverse': 'linear-gradient(135deg, #F8B26A 0%, #FC8462 100%)',
        'gradient-kanors-soft': 'linear-gradient(135deg, #F8B26A 0%, #FC8462 50%, #F8B26A 100%)',
        'gradient-kanors-deep': 'linear-gradient(135deg, #FC8462 0%, #F8B26A 50%, #FC8462 100%)',
        
        // Blue gradients
        'gradient-blue': 'linear-gradient(135deg, #C3D4FE 0%, #40517F 100%)',
        'gradient-blue-soft': 'linear-gradient(135deg, #C3D4FE 0%, #40517F 50%, #C3D4FE 100%)',
        'gradient-blue-deep': 'linear-gradient(135deg, #40517F 0%, #C3D4FE 50%, #40517F 100%)'
      },
      
      // Enhanced shadow system - inspired by the button's subtle shadow
      boxShadow: {
        'vervestacks': '0 4px 6px -1px rgba(139, 92, 246, 0.15), 0 2px 4px -1px rgba(139, 92, 246, 0.1)',
        'vervestacks-lg': '0 10px 15px -3px rgba(139, 92, 246, 0.15), 0 4px 6px -2px rgba(139, 92, 246, 0.1)',
        'vervestacks-xl': '0 20px 25px -5px rgba(139, 92, 246, 0.15), 0 10px 10px -5px rgba(139, 92, 246, 0.1)',
        'vervestacks-2xl': '0 25px 50px -12px rgba(139, 92, 246, 0.3)',
        
        // Component-specific shadows - enhanced for better depth
        'button': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        'button-hover': '0 10px 15px -3px rgba(0, 0, 0, 0.15), 0 4px 6px -2px rgba(0, 0, 0, 0.1)',
        'button-active': '0 2px 4px -1px rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.06)',
        'card': '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
        'card-hover': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        
        // Purple-specific shadows for buttons
        'purple-button': '0 4px 6px -1px rgba(139, 92, 246, 0.2), 0 2px 4px -1px rgba(139, 92, 246, 0.15)',
        'purple-button-hover': '0 10px 15px -3px rgba(139, 92, 246, 0.25), 0 4px 6px -2px rgba(139, 92, 246, 0.2)',
        'purple-button-active': '0 2px 4px -1px rgba(139, 92, 246, 0.2), 0 1px 2px -1px rgba(139, 92, 246, 0.15)'
      },
      
      // Enhanced animation system
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-slow': 'pulse 3s infinite',
        'float': 'float 6s ease-in-out infinite',
        'gradient': 'gradient 3s ease infinite',
        'bounce-gentle': 'bounceGentle 2s ease-in-out infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'shimmer': 'shimmer 2s linear infinite'
      },
      
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        gradient: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        bounceGentle: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-5px)' },
        },
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(139, 92, 246, 0.5)' },
          '100%': { boxShadow: '0 0 20px rgba(139, 92, 246, 0.8)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        }
      },
      
      // Enhanced spacing and sizing
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
        '144': '36rem'
      },
      
      // Enhanced border radius - inspired by the button's soft corners
      borderRadius: {
        'vervestacks': '0.875rem', // Slightly more rounded like the button
        'vervestacks-lg': '1.125rem',
        'vervestacks-xl': '1.375rem',
        'vervestacks-2xl': '1.5rem'
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}
