import { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  message: string;
}

export default class ErrorBoundary extends Component<Props, State> {
  private handleRejection?: (event: PromiseRejectionEvent) => void;

  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, message: '' };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message };
  }

  componentDidMount() {
    this.handleRejection = (event: PromiseRejectionEvent) => {
      const message = event.reason instanceof Error
        ? event.reason.message
        : String(event.reason || 'An unexpected error occurred');
      this.setState({ hasError: true, message });
    };
    window.addEventListener('unhandledrejection', this.handleRejection);
  }

  componentWillUnmount() {
    if (this.handleRejection) {
      window.removeEventListener('unhandledrejection', this.handleRejection);
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="h-screen flex items-center justify-center bg-para-navy" role="alert">
          <div className="text-center">
            <p className="text-red-400 text-lg mb-2">Something went wrong</p>
            <p className="text-gray-500 text-sm mb-4">{this.state.message}</p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-para-teal text-white rounded-lg text-sm hover:bg-para-teal-dark transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
