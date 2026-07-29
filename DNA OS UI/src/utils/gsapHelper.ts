import { gsap } from 'gsap';

/**
 * GSAP Animation Utilities for AgentOS
 */

export const animateWindowSpawn = (element: HTMLElement | null) => {
  if (!element) return;
  gsap.fromTo(
    element,
    { opacity: 0, scale: 0.96, y: 8 },
    { opacity: 1, scale: 1, y: 0, duration: 0.25, ease: 'power2.out' }
  );
};

export const animateTabSwitch = (element: HTMLElement | null) => {
  if (!element) return;
  gsap.fromTo(
    element,
    { opacity: 0, y: 4 },
    { opacity: 1, y: 0, duration: 0.18, ease: 'power1.out' }
  );
};

export const animatePulse = (element: HTMLElement | null) => {
  if (!element) return;
  gsap.to(element, {
    opacity: 0.3,
    yoyo: true,
    repeat: -1,
    duration: 0.8,
    ease: 'power1.inOut',
  });
};

export const animateLogLineEntry = (element: HTMLElement | null) => {
  if (!element) return;
  gsap.fromTo(
    element,
    { opacity: 0, x: -6 },
    { opacity: 1, x: 0, duration: 0.15, ease: 'power1.out' }
  );
};
