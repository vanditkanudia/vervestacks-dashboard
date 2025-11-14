import React from 'react';
import { Link } from 'react-router-dom';
import { 
  Zap, 
  Globe, 
  BarChart3, 
  TrendingUp, 
  Database, 
  FileText, 
  Lightbulb,
  CheckCircle,
  Clock,
  Settings,
  Download,
  Eye
} from 'lucide-react';
import Header from '../components/Header';

const DocumentationPage = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header showNavigation={true} />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Navigation Breadcrumb */}
        <nav className="flex mb-8" aria-label="Breadcrumb">
          <ol className="flex items-center space-x-2">
            <li>
              <Link to="/" className="text-gray-500 hover:text-gray-700">
                Home
              </Link>
            </li>
            <li className="flex items-center">
              <span className="mx-2 text-gray-400">/</span>
              <span className="text-gray-900 font-medium">Documentation</span>
            </li>
          </ol>
        </nav>

        {/* Feature 1.2 Documentation */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          {/* Feature Header */}
          <div className="bg-gradient-to-r from-vervestacks-primary to-vervestacks-secondary px-6 py-8">
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center">
                <Zap className="h-6 w-6 text-white" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-white">
                  Feature 1.2: Hourly Electricity Generation Profile Generator
                </h2>
                <p className="text-white/90 mt-1">
                  Generate comprehensive 8760-hour electricity generation profiles for any country
                </p>
              </div>
            </div>
          </div>

          <div className="p-6">
            {/* Status Badge */}
            <div className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800 mb-6">
              <CheckCircle className="h-4 w-4 mr-2" />
              Complete and Fully Functional
            </div>

            {/* Overview */}
            <div className="mb-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <Eye className="h-5 w-5 mr-2 text-vervestacks-primary" />
                Overview
              </h3>
              <p className="text-gray-700 leading-relaxed">
                The Hourly Electricity Generation Profile Generator is a powerful tool that creates complete 
                8760-hour (annual) electricity generation profiles for any country. It combines real-world 
                data from multiple sources to generate accurate, demand-shaped generation profiles that 
                follow each country's unique electricity consumption patterns.
              </p>
            </div>

            {/* What Users Can Do */}
            <div className="mb-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <Lightbulb className="h-5 w-5 mr-2 text-vervestacks-primary" />
                What You Can Do
              </h3>
              <div className="grid md:grid-cols-2 gap-4">
                <div className="bg-gray-50 rounded-lg p-4">
                  <h4 className="font-medium text-gray-900 mb-2">Generate Annual Profiles</h4>
                  <p className="text-sm text-gray-600">
                    Create 8760-hour electricity generation profiles for any country with real data
                  </p>
                </div>
                <div className="bg-gray-50 rounded-lg p-4">
                  <h4 className="font-medium text-gray-900 mb-2">Custom Generation Targets</h4>
                  <p className="text-sm text-gray-600">
                    Specify custom total generation targets or use actual historical data
                  </p>
                </div>
                <div className="bg-gray-50 rounded-lg p-4">
                  <h4 className="font-medium text-gray-900 mb-2">Interactive Visualizations</h4>
                  <p className="text-sm text-gray-600">
                    View results in interactive charts with zoom, pan, and export capabilities
                  </p>
                </div>
                <div className="bg-gray-50 rounded-lg p-4">
                  <h4 className="font-medium text-gray-900 mb-2">Data Export</h4>
                  <p className="text-sm text-gray-600">
                    Export data for further analysis in external tools and models
                  </p>
                </div>
              </div>
            </div>

            {/* How It Works */}
            <div className="mb-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <Settings className="h-5 w-5 mr-2 text-vervestacks-primary" />
                How It Works
              </h3>
              <div className="space-y-4">
                <div className="flex items-start space-x-3">
                  <div className="w-6 h-6 bg-vervestacks-primary text-white rounded-full flex items-center justify-center text-sm font-bold mt-0.5">
                    1
                  </div>
                  <div>
                    <h4 className="font-medium text-gray-900">Data Collection</h4>
                    <p className="text-sm text-gray-600 mt-1">
                      Gathers electricity generation data from EMBER database, demand profiles from ERA5 weather data, 
                      and renewable potential from REZoning grid analysis
                    </p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <div className="w-6 h-6 bg-vervestacks-primary text-white rounded-full flex items-center justify-center text-sm font-bold mt-0.5">
                    2
                  </div>
                  <div>
                    <h4 className="font-medium text-gray-900">Profile Generation</h4>
                    <p className="text-sm text-gray-600 mt-1">
                      Creates baseline generation profiles (nuclear, hydro) and integrates renewable energy 
                      (solar, wind) with hourly generation shapes
                    </p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <div className="w-6 h-6 bg-vervestacks-primary text-white rounded-full flex items-center justify-center text-sm font-bold mt-0.5">
                    3
                  </div>
                  <div>
                    <h4 className="font-medium text-gray-900">Demand Shaping</h4>
                    <p className="text-sm text-gray-600 mt-1">
                      Applies each country's unique demand pattern to create realistic hourly generation profiles
                    </p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <div className="w-6 h-6 bg-vervestacks-primary text-white rounded-full flex items-center justify-center text-sm font-bold mt-0.5">
                    4
                  </div>
                  <div>
                    <h4 className="font-medium text-gray-900">Analysis & Output</h4>
                    <p className="text-sm text-gray-600 mt-1">
                      Generates comprehensive analysis including coverage metrics, supply curves, and 
                      interactive visualizations
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Data Sources */}
            <div className="mb-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <Database className="h-5 w-5 mr-2 text-vervestacks-primary" />
                Data Sources & Quality
              </h3>
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-medium text-gray-900 mb-3">Primary Data Sources</h4>
                  <ul className="space-y-2 text-sm text-gray-600">
                    <li className="flex items-center">
                      <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                      <strong>EMBER Database:</strong> Official electricity generation statistics (2000-2023)
                    </li>
                    <li className="flex items-center">
                      <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                      <strong>REZoning Grid Data:</strong> High-resolution renewable energy potential
                    </li>
                    <li className="flex items-center">
                      <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                      <strong>ERA5 Weather Data:</strong> Hourly renewable generation shapes
                    </li>
                    <li className="flex items-center">
                      <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                      <strong>IRENA Statistics:</strong> Installed capacity and generation validation
                    </li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium text-gray-900 mb-3">Coverage & Quality</h4>
                  <ul className="space-y-2 text-sm text-gray-600">
                    <li className="flex items-center">
                      <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                      <strong>Global Coverage:</strong> 210+ countries with electricity data
                    </li>
                    <li className="flex items-center">
                      <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                      <strong>Data Quality:</strong> Official national statistics and international databases
                    </li>
                    <li className="flex items-center">
                      <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                      <strong>Real-time Updates:</strong> Latest available data from authoritative sources
                    </li>
                    <li className="flex items-center">
                      <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                      <strong>Validation:</strong> Cross-referenced with multiple data sources
                    </li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Technical Features */}
            <div className="mb-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <TrendingUp className="h-5 w-5 mr-2 text-vervestacks-primary" />
                Technical Features
              </h3>
              <div className="grid md:grid-cols-3 gap-4">
                <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                  <h4 className="font-medium text-blue-900 mb-2">LCOE Optimization</h4>
                  <p className="text-sm text-blue-700">
                    Enhanced LCOE calculations with regional adjustments, policy incentives, and technology variants
                  </p>
                </div>
                <div className="bg-green-50 rounded-lg p-4 border border-green-200">
                  <h4 className="font-medium text-green-900 mb-2">Demand Shaping</h4>
                  <p className="text-sm text-green-700">
                    Generation profiles automatically follow each country's unique demand patterns
                  </p>
                </div>
                <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                  <h4 className="font-medium text-purple-900 mb-2">8760-Hour Precision</h4>
                  <p className="text-sm text-purple-700">
                    Complete annual hourly resolution for accurate energy modeling and analysis
                  </p>
                </div>
              </div>
            </div>

            {/* Usage Examples */}
            <div className="mb-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <BarChart3 className="h-5 w-5 mr-2 text-vervestacks-primary" />
                Usage Examples
              </h3>
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-3">Generate Germany's 2022 Profile</h4>
                <div className="bg-white rounded border p-3 font-mono text-sm">
                  <div className="text-gray-600"># Access the feature</div>
                  <div className="text-gray-800">Navigate to: Generation Profile → Select Country: Germany</div>
                  <div className="text-gray-600"># Set parameters</div>
                  <div className="text-gray-800">Year: 2022</div>
                  <div className="text-gray-800">Total Generation: 566.2 TWh (from EMBER data)</div>
                  <div className="text-gray-600"># Generate profile</div>
                  <div className="text-gray-800">Click "Generate Profile" → Get 8760-hour data</div>
                </div>
                <p className="text-sm text-gray-600 mt-3">
                  The system will automatically create a demand-shaped generation profile using Germany's 
                  actual electricity consumption patterns and integrate renewable energy from REZoning data.
                </p>
              </div>
            </div>

            {/* Output & Analysis */}
            <div className="mb-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <FileText className="h-5 w-5 mr-2 text-vervestacks-primary" />
                Output & Analysis
              </h3>
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-medium text-gray-900 mb-3">Charts & Visualizations</h4>
                  <ul className="space-y-2 text-sm text-gray-600">
                    <li>• Quarterly stacked area charts (supply vs. demand)</li>
                    <li>• Renewable energy supply curves (LCOE vs. capacity)</li>
                    <li>• Interactive line charts with zoom and pan</li>
                    <li>• Statistical analysis and coverage metrics</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium text-gray-900 mb-3">Data Export</h4>
                  <ul className="space-y-2 text-sm text-gray-600">
                    <li>• CSV format for external analysis</li>
                    <li>• 8760-hour generation profiles</li>
                    <li>• Fuel breakdown and renewable integration</li>
                    <li>• Coverage and surplus hour analysis</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Integration */}
            <div className="mb-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <Globe className="h-5 w-5 mr-2 text-vervestacks-primary" />
                Integration with VerveStacks
              </h3>
              <p className="text-gray-700 leading-relaxed mb-4">
                This feature is fully integrated with the VerveStacks ecosystem, providing seamless 
                access to the timeslice design module and advanced energy system analysis capabilities.
              </p>
              <div className="grid md:grid-cols-3 gap-4">
                <div className="text-center p-4 bg-vervestacks-primary/10 rounded-lg">
                  <div className="w-8 h-8 bg-vervestacks-primary text-white rounded-lg flex items-center justify-center mx-auto mb-2">
                    <Clock className="h-4 w-4" />
                  </div>
                  <h4 className="font-medium text-gray-900">Timeslice Design</h4>
                  <p className="text-sm text-gray-600">Direct integration with VerveStacks timeslice processor</p>
                </div>
                <div className="text-center p-4 bg-vervestacks-secondary/10 rounded-lg">
                  <div className="w-8 h-8 bg-vervestacks-secondary text-white rounded-lg flex items-center justify-center mx-auto mb-2">
                    <Settings className="h-4 w-4" />
                  </div>
                  <h4 className="font-medium text-gray-900">Configuration System</h4>
                  <p className="text-sm text-gray-600">Centralized configuration for consistent analysis</p>
                </div>
                <div className="text-center p-4 bg-vervestacks-accent/10 rounded-lg">
                  <div className="w-8 h-8 bg-vervestacks-accent text-white rounded-lg flex items-center justify-center mx-auto mb-2">
                    <Download className="h-4 w-4" />
                  </div>
                  <h4 className="font-medium text-gray-900">Data Lineage</h4>
                  <p className="text-sm text-gray-600">Complete traceability of data sources and processing</p>
                </div>
              </div>
            </div>

            {/* Call to Action */}
            <div className="bg-gradient-to-r from-vervestacks-primary/10 to-vervestacks-secondary/10 rounded-lg p-6 text-center">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Ready to Generate Your First Profile?
              </h3>
              <p className="text-gray-600 mb-4">
                Experience the power of 8760-hour electricity generation analysis with real-world data
              </p>
              <Link
                to="/generation-profile"
                className="inline-flex items-center px-6 py-3 bg-vervestacks-primary text-white font-medium rounded-lg hover:bg-vervestacks-primary-dark transition-colors duration-200"
              >
                <Zap className="h-5 w-5 mr-2" />
                Try Generation Profile Generator
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocumentationPage;
