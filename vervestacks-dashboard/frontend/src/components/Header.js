import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { User, LogOut, Settings, Menu, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const Header = ({ showNavigation = true }) => {
  const { user, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showMobileMenu, setShowMobileMenu] = useState(false);

  const navigation = [
    { name: 'Home', href: '/' },
    { name: 'Explore', href: '/explore' },
    { name: 'About', href: '/about' },
    { name: 'Documentation', href: '/docs' },
  ];

  const handleLogout = () => {
    logout();
    setShowUserMenu(false);
    navigate('/');
  };

  return (
    <header className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo - Always visible */}
          <Link to="/" className="flex items-center space-x-3">
            <div className="flex items-center space-x-2">
              <img 
                src="/images/Kanors_logo.png" 
                alt="KANORS Logo" 
                className="h-8 w-auto"
              />
              <div>
                <span className="text-gray-400 text-sm font-medium">KANORS</span>
                <h1 className="text-xl font-bold text-vervestacks-dark-blue -mt-1">
                  VERVESTACKS
                </h1>
              </div>
            </div>
          </Link>

          {/* Right side content - Only show when navigation is enabled */}
          {showNavigation ? (
            <>
              {/* Desktop Navigation */}
              <nav className="hidden md:flex items-center space-x-8">
                {navigation.map((item) => (
                  <Link
                    key={item.name}
                    to={item.href}
                    className="text-gray-600 hover:text-vervestacks-primary transition-colors duration-200 font-medium"
                  >
                    {item.name}
                  </Link>
                ))}
              </nav>

              {/* User Menu / Auth Buttons */}
              <div className="flex items-center space-x-4">
                {isAuthenticated ? (
                  <div className="relative">
                    <button
                      onClick={() => setShowUserMenu(!showUserMenu)}
                      className="flex items-center space-x-2 text-gray-600 hover:text-vervestacks-primary transition-colors duration-200"
                    >
                      <User className="h-5 w-5" />
                      <span className="hidden sm:block font-medium">
                        {user?.firstName || user?.email}
                      </span>
                    </button>

                    {/* User Dropdown */}
                    {showUserMenu && (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50"
                      >
                        <div className="px-4 py-2 border-b border-gray-100">
                          <p className="text-sm font-medium text-gray-900">
                            {user?.firstName} {user?.lastName}
                          </p>
                          <p className="text-sm text-gray-500">{user?.email}</p>
                        </div>
                        
                        <Link
                          to="/profile"
                          className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                          onClick={() => setShowUserMenu(false)}
                        >
                          <Settings className="h-4 w-4 mr-3" />
                          Profile Settings
                        </Link>
                        
                        <button
                          onClick={handleLogout}
                          className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                        >
                          <LogOut className="h-4 w-4 mr-3" />
                          Sign Out
                        </button>
                      </motion.div>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center space-x-3">
                    <Link
                      to="/login"
                      className="text-gray-600 hover:text-vervestacks-primary transition-colors duration-200 font-medium"
                    >
                      Sign In
                    </Link>
                    <Link
                      to="/register"
                      className="btn-primary"
                    >
                      Get Started
                    </Link>
                  </div>
                )}

                {/* Mobile Menu Button */}
                <button
                  onClick={() => setShowMobileMenu(!showMobileMenu)}
                  className="md:hidden p-2 text-gray-600 hover:text-vervestacks-primary transition-colors duration-200"
                >
                  {showMobileMenu ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
                </button>
              </div>
            </>
          ) : (
            /* Minimal header when navigation is hidden */
            <div className="flex items-center">
              <span className="text-sm text-gray-500">Energy Modeling Platform</span>
            </div>
          )}
        </div>

        {/* Mobile Navigation - Only show when navigation is enabled */}
        {showNavigation && showMobileMenu && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden border-t border-gray-200 py-4"
          >
            <nav className="flex flex-col space-y-3">
              {navigation.map((item) => (
                <Link
                  key={item.name}
                  to={item.href}
                  className="text-gray-600 hover:text-vervestacks-primary transition-colors duration-200 font-medium px-4 py-2"
                  onClick={() => setShowMobileMenu(false)}
                >
                  {item.name}
                </Link>
              ))}
              
              {/* Mobile Auth Section */}
              <div className="border-t border-gray-200 pt-3 mt-3">
                {isAuthenticated ? (
                  <div className="px-4 py-2">
                    <p className="text-sm font-medium text-gray-900">
                      {user?.firstName} {user?.lastName}
                    </p>
                    <p className="text-sm text-gray-500">{user?.email}</p>
                    <button
                      onClick={handleLogout}
                      className="mt-2 text-sm text-red-600 hover:text-red-700"
                    >
                      Sign Out
                    </button>
                  </div>
                ) : (
                  <div className="flex flex-col space-y-2 px-4">
                    <Link
                      to="/login"
                      className="text-gray-600 hover:text-vervestacks-primary transition-colors duration-200 font-medium py-2"
                      onClick={() => setShowMobileMenu(false)}
                    >
                      Sign In
                    </Link>
                    <Link
                      to="/register"
                      className="btn-primary text-center py-2"
                      onClick={() => setShowMobileMenu(false)}
                    >
                      Get Started
                    </Link>
                  </div>
                )}
              </div>
            </nav>
          </motion.div>
        )}
      </div>
    </header>
  );
};

export default Header;