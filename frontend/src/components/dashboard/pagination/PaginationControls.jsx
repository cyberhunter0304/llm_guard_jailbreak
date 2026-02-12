import React from 'react';

/**
 * PaginationControls - Clean pagination UI component
 * Shows current page, total pages, and navigation buttons
 */
const PaginationControls = React.memo(({ 
  currentPage, 
  totalPages, 
  onPageChange,
  itemsPerPage,
  totalItems
}) => {
  if (totalPages <= 1) return null;

  // Calculate item range
  const startItem = (currentPage - 1) * itemsPerPage + 1;
  const endItem = Math.min(currentPage * itemsPerPage, totalItems);

  // Generate page buttons (show max 7 buttons)
  const getPageNumbers = () => {
    const pages = [];
    const maxButtons = 7;
    let startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2));
    let endPage = Math.min(totalPages, startPage + maxButtons - 1);
    
    if (endPage - startPage + 1 < maxButtons) {
      startPage = Math.max(1, endPage - maxButtons + 1);
    }

    if (startPage > 1) {
      pages.push(1);
      if (startPage > 2) pages.push('...');
    }

    for (let i = startPage; i <= endPage; i++) {
      pages.push(i);
    }

    if (endPage < totalPages) {
      if (endPage < totalPages - 1) pages.push('...');
      pages.push(totalPages);
    }

    return pages;
  };

  return (
    <div style={styles.container}>
      <div style={styles.info}>
        <span style={styles.infoText}>
          Showing {startItem}–{endItem} of {totalItems} results
        </span>
      </div>

      <div style={styles.controls}>
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          style={{
            ...styles.button,
            ...styles.navButton,
            ...(!styles.button.opacity && currentPage === 1 ? styles.disabled : {})
          }}
          title="Previous page"
        >
          ← Previous
        </button>

        <div style={styles.pageButtons}>
          {getPageNumbers().map((page, idx) => (
            page === '...' ? (
              <span key={idx} style={styles.ellipsis}>…</span>
            ) : (
              <button
                key={page}
                onClick={() => onPageChange(page)}
                style={{
                  ...styles.button,
                  ...styles.pageButton,
                  ...(currentPage === page ? styles.activePageButton : styles.inactivePageButton)
                }}
                title={`Go to page ${page}`}
              >
                {page}
              </button>
            )
          ))}
        </div>

        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          style={{
            ...styles.button,
            ...styles.navButton,
            ...(currentPage === totalPages ? styles.disabled : {})
          }}
          title="Next page"
        >
          Next →
        </button>
      </div>

      <div style={styles.pageInfo}>
        <span style={styles.pageText}>
          Page {currentPage} of {totalPages}
        </span>
      </div>
    </div>
  );
});

PaginationControls.displayName = 'PaginationControls';

const styles = {
  container: {
    marginTop: '30px',
    padding: '20px',
    backgroundColor: '#fffbf5',
    borderRadius: '8px',
    display: 'flex',
    flexDirection: 'column',
    gap: '15px',
    alignItems: 'center',
    border: '1px solid #fed7aa'
  },
  info: {
    width: '100%',
    textAlign: 'center'
  },
  infoText: {
    fontSize: '13px',
    color: '#78716c',
    fontWeight: '500'
  },
  controls: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    justifyContent: 'center',
    width: '100%'
  },
  button: {
    padding: '8px 12px',
    border: '1px solid #fde68a',
    borderRadius: '6px',
    backgroundColor: '#fff',
    color: '#78716c',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    transition: 'all 0.2s ease',
    userSelect: 'none'
  },
  navButton: {
    minWidth: '100px'
  },
  pageButton: {
    minWidth: '36px',
    height: '36px',
    padding: '0',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  },
  activePageButton: {
    background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
    color: '#fff',
    borderColor: 'transparent',
    fontWeight: 'bold',
    boxShadow: '0 4px 12px rgba(249,115,22,0.25)'
  },
  inactivePageButton: {
    ':hover': {
      backgroundColor: 'rgba(249,115,22,0.05)',
      borderColor: '#f97316',
      color: '#f97316'
    }
  },
  disabled: {
    opacity: '0.5',
    cursor: 'not-allowed',
    backgroundColor: '#fef3c7',
    borderColor: '#fde68a'
  },
  ellipsis: {
    color: '#a8a29e',
    padding: '0 4px',
    fontSize: '14px'
  },
  pageButtons: {
    display: 'flex',
    gap: '4px',
    alignItems: 'center'
  },
  pageInfo: {
    width: '100%',
    textAlign: 'right'
  },
  pageText: {
    fontSize: '12px',
    color: '#a8a29e',
    fontStyle: 'italic'
  }
};

export default PaginationControls;
