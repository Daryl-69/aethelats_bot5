import React from 'react';

const HorseLoader = () => {
  return (
    <div className="horse-shimmer-container flex items-center justify-center w-full h-full">
      <img 
        src="/assets/horse_animated.svg" 
        alt="Aethel Shield Animation"
        className="horse-loader-img w-full h-full"
        style={{ objectFit: 'contain' }}
      />
    </div>
  );
};

export default HorseLoader;